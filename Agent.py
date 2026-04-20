#!/usr/bin/env python3
"""
CFAO Process Monitor Agent

Autonomous agent that monitors CFAO open processes every 30 minutes,
detects stuck processes (>20 minutes), and sends email notifications.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from config import Config


class CFAOProcessMonitor:
    """Main agent class for monitoring CFAO processes"""

    def __init__(self, test_mode=False):
        self.config = Config()
        self.config.validate()
        self.setup_logging()
        self.state = self.load_state()
        self.test_mode = test_mode

        # Ensure directories exist
        os.makedirs(self.config.REPORT_DIR, exist_ok=True)
        os.makedirs(self.config.SCREENSHOT_DIR, exist_ok=True)

    def setup_logging(self):
        """Configure logging to both file and console"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_state(self) -> Dict:
        """Load persistent state from JSON file"""
        if os.path.exists(self.config.STATE_FILE):
            try:
                with open(self.config.STATE_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load state file: {e}")
        return {'last_all_clear_timestamp': None}

    def save_state(self):
        """Save persistent state to JSON file"""
        try:
            with open(self.config.STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            self.logger.error(f"Failed to save state file: {e}")

    def parse_time_to_minutes(self, time_str: str) -> Optional[int]:
        """Parse time string (HH:MM:SS) to total minutes"""
        try:
            if not time_str or time_str.strip() == '':
                return None

            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 60 + minutes + seconds // 60
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes + seconds // 60
            else:
                self.logger.warning(f"Unexpected time format: {time_str}")
                return None
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    def login_to_cfa0(self, page: Page) -> bool:
        """Login to Oracle IDCS and navigate to CFAO processes page"""
        try:
            self.logger.info("Navigating to CFAO processes page directly...")
            # Try navigating directly to the processes page - it might redirect to login
            page.goto(self.config.CFAO_PROCESSES_URL, timeout=self.config.BROWSER_TIMEOUT)

            # Wait for page to load and any redirects to complete
            page.wait_for_load_state('domcontentloaded', timeout=self.config.BROWSER_TIMEOUT)
            page.wait_for_load_state('networkidle', timeout=self.config.BROWSER_TIMEOUT)

            # Additional wait for redirects
            time.sleep(3)

            # Check current URL - if we're on login page, we need to authenticate
            current_url = page.url
            if "signin" in current_url.lower() or "login" in current_url.lower():
                self.logger.info("Redirected to login page, attempting to login...")

                # Wait for login form to load
                time.sleep(2)  # Additional wait for dynamic content

                # Debug: Log page info
                self.logger.info(f"Login URL: {page.url}")
                self.logger.info(f"Page title: {page.title()}")

                # Try to find and fill login form
                try:
                    # Wait for form elements to be visible
                    page.wait_for_selector('input[type="text"], input[name="username"]', timeout=10000)

                    # Look for username field
                    username_selectors = ['input[type="text"]', 'input[name="username"]', 'input[id="username"]', '#username']
                    username_field = None
                    for selector in username_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                username_field = page.locator(selector).first
                                break
                        except:
                            continue

                    if not username_field:
                        self.logger.error("Username field not found")
                        return False

                    self.logger.info("Found username field, filling credentials...")
                    username_field.fill(self.config.ORACLE_USERNAME)
                    time.sleep(1)

                    # Look for password field
                    password_selectors = ['input[type="password"]', 'input[name="password"]', 'input[id="password"]', '#password']
                    password_field = None
                    for selector in password_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                password_field = page.locator(selector).first
                                break
                        except:
                            continue

                    if not password_field:
                        self.logger.error("Password field not found")
                        return False

                    self.logger.info("Found password field, filling credentials...")
                    password_field.fill(self.config.ORACLE_PASSWORD)
                    time.sleep(1)

                    # Look for submit button
                    submit_selectors = ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Sign In")', 'button:has-text("Login")', '#signin', '#login']
                    submit_button = None
                    for selector in submit_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                submit_button = page.locator(selector).first
                                break
                        except:
                            continue

                    if not submit_button:
                        self.logger.error("Submit button not found")
                        return False

                    self.logger.info(f"Found submit button, clicking it...")
                    submit_button.click()

                    # Wait for navigation after login
                    page.wait_for_load_state('networkidle', timeout=self.config.BROWSER_TIMEOUT)
                    time.sleep(5)  # Wait for any additional redirects or 2FA

                    # Check for common post-login elements or URL changes
                    max_wait = 30  # seconds
                    for i in range(max_wait):
                        current_url = page.url
                        current_title = page.title()
                        self.logger.debug(f"Waiting for login completion... {i+1}/{max_wait} - URL: {current_url}, Title: {current_title}")

                        # Check if we're no longer on login page
                        if "signin" not in current_url.lower() and "login" not in current_url.lower():
                            self.logger.info("Login successful! URL changed away from login page.")
                            return True

                        # Check if title indicates we're on the application
                        if "open processes" in current_title.lower() or "cfao" in current_title.lower():
                            self.logger.info("Login successful! Page title indicates processes page.")
                            return True

                        # Check for error messages
                        error_selectors = ['.error', '.alert', '[class*="error"]', '[class*="alert"]']
                        for selector in error_selectors:
                            try:
                                if page.locator(selector).count() > 0:
                                    error_text = page.locator(selector).first.text_content()
                                    if error_text.strip():
                                        self.logger.error(f"Login error detected: {error_text}")
                                        return False
                            except:
                                continue

                        time.sleep(1)

                    # If we get here, login may have succeeded but page didn't change as expected
                    self.logger.warning("Login completion uncertain - proceeding anyway")
                    return True

                except Exception as e:
                    self.logger.error(f"Error during login form interaction: {e}")
                    return False
            else:
                self.logger.info("Direct navigation successful - already logged in or session active")
                return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def refresh_processes_page(self, page: Page) -> bool:
        """Click the refresh button and wait for table reload"""
        try:
            self.logger.info("Looking for refresh button...")

            # Look for refresh button - try multiple selectors
            refresh_selectors = [
                'button:has-text("Refresh")',
                'input[value="Refresh"]',
                'button[title*="refresh" i]',
                'button[class*="refresh" i]',
                '#refreshButton',
                'button[type="submit"]:has-text("Refresh")'
            ]

            refresh_button = None
            for selector in refresh_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        refresh_button = page.locator(selector).first
                        break
                except:
                    continue

            if not refresh_button:
                self.logger.warning("Refresh button not found, trying to reload page")
                page.reload()
                page.wait_for_load_state('networkidle', timeout=self.config.BROWSER_TIMEOUT)
                return True

            self.logger.info("Clicking refresh button...")
            refresh_button.click()

            # Wait for table to reload - look for common table indicators
            self.logger.info("Waiting for table reload...")
            page.wait_for_load_state('networkidle', timeout=self.config.BROWSER_TIMEOUT)

            # Additional wait for dynamic content
            time.sleep(3)

            return True

        except Exception as e:
            self.logger.error(f"Failed to refresh processes page: {e}")
            return False

    def extract_processes_data(self, page: Page) -> List[Dict]:
        """Extract process data from the CFAO processes table"""
        processes = []

        try:
            self.logger.info("Extracting process data from table...")

            # Debug: Take screenshot and log page info
            self.logger.info(f"Processes page URL: {page.url}")
            self.logger.info(f"Page title: {page.title()}")

            # Check if we're actually on a processes page
            page_text = page.locator('body').text_content().lower()
            if 'process' not in page_text and 'open' not in page_text:
                self.logger.warning("Page does not appear to contain process information")
                return processes

            # Look for the processes table - try multiple selectors
            table_selectors = [
                'table',
                '.table',
                '#processesTable',
                'table[class*="process" i]',
                'table:has(th:contains("Process ID"))',
                'table:has(th:contains("ID"))'
            ]

            table = None
            for selector in table_selectors:
                try:
                    tables = page.locator(selector).all()
                    self.logger.info(f"Found {len(tables)} table(s) with selector '{selector}'")
                    if len(tables) > 0:
                        table = tables[0]
                        self.logger.info(f"Using table with selector '{selector}'")
                        break
                except Exception as e:
                    self.logger.debug(f"Selector '{selector}' failed: {e}")
                    continue

            if not table:
                self.logger.warning("No processes table found on main page, checking frames...")
                # Check frames
                frames = page.frames
                self.logger.info(f"Found {len(frames)} iframe(s) on the page")
                for i, frame in enumerate(frames):
                    try:
                        frame_tables = frame.locator('table').all()
                        self.logger.info(f"Frame {i}: Found {len(frame_tables)} table(s)")
                        if len(frame_tables) > 0:
                            # Check if this frame has process data
                            frame_text = frame.locator('body').text_content().lower()
                            if 'process' in frame_text:
                                table = frame_tables[0]
                                self.logger.info(f"Using table from frame {i}")
                                break
                    except Exception as e:
                        self.logger.debug(f"Frame {i} check failed: {e}")
                        continue

            if not table:
                self.logger.warning("No processes table found in any frame")
                return processes

            # Extract table rows (skip header)
            rows = table.locator('tbody tr, tr').all()
            self.logger.info(f"Found {len(rows)} total rows in table")

            if len(rows) <= 1:  # No data rows
                self.logger.info("No process rows found in table")
                return processes

            self.logger.info(f"Processing {len(rows)-1} data rows")

            for row_idx, row in enumerate(rows[1:], 1):  # Skip header row
                try:
                    cells = row.locator('td').all()
                    self.logger.debug(f"Row {row_idx}: Found {len(cells)} cells")
                    if len(cells) < 6:  # Minimum expected columns
                        self.logger.debug(f"Row {row_idx}: Skipping - not enough cells")
                        continue

                    process_data = {
                        'description': cells[0].text_content().strip() if len(cells) > 0 else '',
                        'process_id': cells[1].text_content().strip() if len(cells) > 1 else '',
                        'log_id': cells[2].text_content().strip() if len(cells) > 2 else '',
                        'server': cells[3].text_content().strip() if len(cells) > 3 else '',
                        'state': cells[4].text_content().strip() if len(cells) > 4 else '',
                        'time': cells[5].text_content().strip() if len(cells) > 5 else '',
                        'locks': cells[6].text_content().strip() if len(cells) > 6 else ''
                    }

                    self.logger.debug(f"Row {row_idx}: Process ID = '{process_data['process_id']}'")

                    # Only add if we have at least a process ID
                    if process_data['process_id']:
                        processes.append(process_data)
                        self.logger.debug(f"Added process: {process_data['process_id']}")
                    else:
                        self.logger.debug(f"Skipped row {row_idx} - no process ID")

                except Exception as e:
                    self.logger.warning(f"Failed to extract data from row {row_idx}: {e}")
                    continue

            self.logger.info(f"Successfully extracted {len(processes)} processes")
            return processes

        except Exception as e:
            self.logger.error(f"Failed to extract processes data: {e}")
            return processes

    def check_for_stuck_processes(self, processes: List[Dict]) -> List[Dict]:
        """Check for processes running longer than threshold"""
        stuck_processes = []

        for process in processes:
            time_str = process.get('time', '')
            minutes = self.parse_time_to_minutes(time_str)

            if minutes is None:
                self.logger.warning(f"Could not parse time for process {process.get('process_id', 'unknown')}: {time_str}")
                continue

            if minutes > self.config.STUCK_PROCESS_THRESHOLD_MINUTES:
                stuck_processes.append({
                    **process,
                    'elapsed_minutes': minutes
                })

        return stuck_processes

    def send_stuck_process_alert(self, stuck_processes: List[Dict]):
        """Save alert report for stuck processes"""
        if not stuck_processes:
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"cfaoprocesses_alert_{timestamp}.txt"
        report_path = os.path.join(self.config.REPORT_DIR, report_filename)

        body_lines = [
            f"ALERT: {len(stuck_processes)} CFAO Process(es) Stuck",
            "",
            "The following CFAO processes have been running for more than 20 minutes:",
            "",
        ]

        for process in stuck_processes:
            body_lines.extend([
                f"Process ID: {process['process_id']}",
                f"Description: {process['description']}",
                f"Elapsed Time: {process['elapsed_minutes']} minutes",
                f"Server: {process['server']}",
                f"State: {process['state']}",
                "",
            ])

        body_lines.extend([
            f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Please investigate immediately."
        ])

        body = "\n".join(body_lines)

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(body)
            self.logger.warning(f"Alert report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save alert report: {e}")

    def send_all_clear_notification(self):
        """Save all-clear report"""
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        report_filename = f"cfaoprocesses_allclear_{timestamp}.txt"
        report_path = os.path.join(self.config.REPORT_DIR, report_filename)

        body = "\n".join([
            "CFAO Processes Status: All Clear",
            "",
            "All CFAO open processes are running normally (<=20 minutes).",
            "",
            f"Checked at: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Next all-clear report will be saved in 1 hour if status remains clear."
        ])

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(body)
            self.logger.info(f"All-clear report saved: {report_path}")
            self.state['last_all_clear_timestamp'] = now.isoformat()
            self.save_state()
        except Exception as e:
            self.logger.error(f"Failed to save all-clear report: {e}")

    def save_monitoring_report(self, page: Page, processes: List[Dict], stuck_processes: List[Dict]):
        """Save a general monitoring report and screenshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save screenshot
        screenshot_filename = f"cfaoprocesses_{timestamp}.png"
        screenshot_path = os.path.join(self.config.SCREENSHOT_DIR, screenshot_filename)

        try:
            page.screenshot(path=screenshot_path)
            self.logger.info(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {e}")

        # Save report
        report_filename = f"cfaoprocesses_report_{timestamp}.txt"
        report_path = os.path.join(self.config.REPORT_DIR, report_filename)

        report_lines = [
            "CFAO Process Monitor Report",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Process URL: {page.url}",
            f"Total Processes: {len(processes)}",
            f"Stuck Processes: {len(stuck_processes)}",
            "",
            f"Screenshot: {screenshot_path}",
            "",
        ]

        if stuck_processes:
            report_lines.append("Stuck Processes:")
            for process in stuck_processes:
                report_lines.extend([
                    f"  ID: {process['process_id']}",
                    f"  Description: {process['description']}",
                    f"  Time: {process['elapsed_minutes']} minutes",
                    f"  Server: {process['server']}",
                    "",
                ])
        else:
            report_lines.append("No stuck processes detected.")

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            self.logger.info(f"Report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

    def save_test_report(self, processes: List[Dict], stuck_processes: List[Dict]):
        """Save a test monitoring report (without screenshot)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save report
        report_filename = f"cfaoprocesses_report_{timestamp}.txt"
        report_path = os.path.join(self.config.REPORT_DIR, report_filename)

        report_lines = [
            "CFAO Process Monitor Report (TEST MODE)",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "Process URL: N/A (test mode)",
            f"Total Processes: {len(processes)}",
            f"Stuck Processes: {len(stuck_processes)}",
            "",
            "Screenshot: N/A (test mode)",
            "",
        ]

        if stuck_processes:
            report_lines.append("Stuck Processes:")
            for process in stuck_processes:
                report_lines.extend([
                    f"  ID: {process['process_id']}",
                    f"  Description: {process['description']}",
                    f"  Time: {process['elapsed_minutes']} minutes",
                    f"  Server: {process['server']}",
                    "",
                ])
        else:
            report_lines.append("No stuck processes detected.")

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))
            self.logger.info(f"Report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

    def should_send_all_clear(self) -> bool:
        """Check if all-clear notification should be sent"""
        last_clear = self.state.get('last_all_clear_timestamp')
        if not last_clear:
            return True

        try:
            last_clear_dt = datetime.fromisoformat(last_clear)
            hours_since = (datetime.now() - last_clear_dt).total_seconds() / 3600
            return hours_since >= self.config.ALL_CLEAR_INTERVAL_HOURS
        except (ValueError, TypeError):
            self.logger.warning("Invalid last_all_clear_timestamp, sending notification")
            return True

    def run_monitoring_cycle(self):
        """Main monitoring cycle"""
        self.logger.info("Starting monitoring cycle...")

        # Check if we should run in test mode (no real browser)
        if self.test_mode:
            self.logger.info("Running in TEST_MODE - simulating browser operations")
            return self.run_test_cycle()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.config.BROWSER_HEADLESS)
            context = browser.new_context()
            page = context.new_page()

            try:
                # Step 1: Login and navigate
                if not self.login_to_cfa0(page):
                    self.logger.error("Failed to login, skipping this cycle")
                    return

                # Step 2: Refresh data
                if not self.refresh_processes_page(page):
                    self.logger.error("Failed to refresh processes page, skipping this cycle")
                    return

                # Step 3: Extract process data
                processes = self.extract_processes_data(page)
                self.logger.info(f"Found {len(processes)} open processes")

                # Step 4: Check for stuck processes
                stuck_processes = self.check_for_stuck_processes(processes)

                # Step 5: Save monitoring report and screenshot
                self.save_monitoring_report(page, processes, stuck_processes)

                if stuck_processes:
                    # Step 6a: Send alert for stuck processes
                    self.logger.warning(f"Found {len(stuck_processes)} stuck processes")
                    self.send_stuck_process_alert(stuck_processes)
                else:
                    # Step 6b: Check if all-clear notification should be sent
                    if self.should_send_all_clear():
                        self.logger.info("Sending all-clear notification")
                        self.send_all_clear_notification()
                    else:
                        self.logger.info("System healthy, no notification needed")

            except Exception as e:
                self.logger.error(f"Monitoring cycle failed: {e}")
            finally:
                context.close()
                browser.close()

        self.logger.info("Monitoring cycle completed")

    def run_test_cycle(self):
        """Test cycle that simulates browser operations without real web access"""
        self.logger.info("Simulating login and navigation...")
        time.sleep(1)  # Simulate login time

        self.logger.info("Simulating page refresh...")
        time.sleep(1)  # Simulate refresh time

        # Generate mock process data for testing
        processes = self.generate_mock_processes()
        self.logger.info(f"Found {len(processes)} open processes")

        # Step 4: Check for stuck processes
        stuck_processes = self.check_for_stuck_processes(processes)

        # Step 5: Save monitoring report (without page)
        self.save_test_report(processes, stuck_processes)

        if stuck_processes:
            # Step 6a: Send alert for stuck processes
            self.logger.warning(f"Found {len(stuck_processes)} stuck processes")
            self.send_stuck_process_alert(stuck_processes)
        else:
            # Step 6b: Check if all-clear notification should be sent
            if self.should_send_all_clear():
                self.logger.info("Sending all-clear notification")
                self.send_all_clear_notification()
            else:
                self.logger.info("System healthy, no notification needed")

        self.logger.info("Test monitoring cycle completed")

    def generate_mock_processes(self) -> List[Dict]:
        """Generate mock process data for testing"""
        import random

        # Sometimes generate stuck processes, sometimes not
        has_stuck = random.choice([True, False])

        if has_stuck:
            # Generate some stuck processes
            processes = [
                {
                    'description': 'Order Processing Batch',
                    'process_id': 'PROC_001',
                    'log_id': 'LOG_12345',
                    'server': 'SERVER_A',
                    'state': 'RUNNING',
                    'time': '00:25:30',  # 25 minutes - STUCK
                    'locks': '2'
                },
                {
                    'description': 'Data Synchronization',
                    'process_id': 'PROC_002',
                    'log_id': 'LOG_12346',
                    'server': 'SERVER_B',
                    'state': 'RUNNING',
                    'time': '01:45:15',  # 105 minutes - STUCK
                    'locks': '1'
                },
                {
                    'description': 'Report Generation',
                    'process_id': 'PROC_003',
                    'log_id': 'LOG_12347',
                    'server': 'SERVER_A',
                    'state': 'RUNNING',
                    'time': '00:05:20',  # 5 minutes - OK
                    'locks': '0'
                }
            ]
        else:
            # Generate only healthy processes
            processes = [
                {
                    'description': 'Daily Backup',
                    'process_id': 'PROC_004',
                    'log_id': 'LOG_12348',
                    'server': 'SERVER_C',
                    'state': 'RUNNING',
                    'time': '00:12:45',  # 12 minutes - OK
                    'locks': '0'
                },
                {
                    'description': 'Cache Refresh',
                    'process_id': 'PROC_005',
                    'log_id': 'LOG_12349',
                    'server': 'SERVER_A',
                    'state': 'RUNNING',
                    'time': '00:08:30',  # 8 minutes - OK
                    'locks': '0'
                }
            ]

        return processes

    def run_scheduled(self):
        """Run the agent with scheduling"""
        self.logger.info("Starting CFAO Process Monitor Agent")
        self.logger.info(f"Check interval: {self.config.CHECK_INTERVAL_MINUTES} minutes")
        self.logger.info(f"Stuck threshold: {self.config.STUCK_PROCESS_THRESHOLD_MINUTES} minutes")

        # Run initial cycle
        self.run_monitoring_cycle()

        # Schedule subsequent runs
        scheduler = BlockingScheduler()
        trigger = IntervalTrigger(minutes=self.config.CHECK_INTERVAL_MINUTES)

        scheduler.add_job(
            self.run_monitoring_cycle,
            trigger=trigger,
            id='cfao_monitor',
            name='CFAO Process Monitor',
            max_instances=1,
            coalesce=True
        )

        self.logger.info("Scheduler started, agent running autonomously")
        scheduler.start()

    def run_once(self):
        """Run a single monitoring cycle for testing"""
        self.logger.info("Running single monitoring cycle for testing")
        self.run_monitoring_cycle()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='CFAO Process Monitor Agent')
    parser.add_argument('--once', action='store_true', help='Run a single monitoring cycle')
    parser.add_argument('--test', action='store_true', help='Run in test mode with mock data')

    args = parser.parse_args()

    agent = CFAOProcessMonitor(test_mode=args.test)

    if args.once:
        agent.run_once()
    else:
        agent.run_scheduled()