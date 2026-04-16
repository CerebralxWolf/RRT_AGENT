import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the CFAO Process Monitor Agent"""

    # Oracle IDCS Login Credentials
    ORACLE_USERNAME = os.getenv('ORACLE_USERNAME', 'AGENT_TEST')
    ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', 'Automation@123')

    # CFAO URLs
    LOGIN_URL = os.getenv('LOGIN_URL', 'https://idcs-040d903d6f0648ab9a72f68b2b0f322c.identity.oraclecloud.com/ui/v1/signin')
    CFAO_PROCESSES_URL = os.getenv('CFAO_PROCESSES_URL', 'https://otmgtm-test-procureonecfao.otmgtm.eu-frankfurt-1.ocs.oraclecloud.com/GC3/glog.webserver.finder.WindowOpenFramesetServlet?url=glog.webserver.process.walker.ProcessWalkerDiagServlet&is_new_window=true')

    # Email Configuration
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USER)
    EMAIL_TO = os.getenv('EMAIL_TO', 'p.harshith.kumar@accenture.com')

    # Agent Configuration
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 30))
    STUCK_PROCESS_THRESHOLD_MINUTES = int(os.getenv('STUCK_PROCESS_THRESHOLD_MINUTES', 20))
    ALL_CLEAR_INTERVAL_HOURS = int(os.getenv('ALL_CLEAR_INTERVAL_HOURS', 1))

    # File Paths
    STATE_FILE = os.getenv('STATE_FILE', 'state.json')
    LOG_FILE = os.getenv('LOG_FILE', 'agent.log')

    # Browser Configuration
    BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'
    BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', 30000))  # 30 seconds

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        required = ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASSWORD']
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Validate URLs
        if not cls.LOGIN_URL.startswith('https://'):
            raise ValueError("LOGIN_URL must be a valid HTTPS URL")
        if not cls.CFAO_PROCESSES_URL.startswith('https://'):
            raise ValueError("CFAO_PROCESSES_URL must be a valid HTTPS URL")