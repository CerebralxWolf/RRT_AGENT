# CFAO Process Monitor Agent

An autonomous Python agent that monitors CFAO open processes every 30 minutes, detects stuck processes (>20 minutes), and sends email notifications.

## Features

- **Autonomous Operation**: Runs 24/7 with built-in scheduling
- **Browser Automation**: Uses Playwright to login to Oracle IDCS and extract process data
- **Stuck Process Detection**: Alerts immediately when processes exceed 20-minute threshold
- **All-Clear Notifications**: Hourly reassurance messages when all processes are healthy
- **State Persistence**: Maintains timestamp of last all-clear message across restarts
- **Email Notifications**: Configurable SMTP email alerts
- **Docker Deployment**: Containerized for easy deployment and scaling
- **Comprehensive Logging**: File and console logging for monitoring

## Requirements

- Python 3.11+
- Docker and Docker Compose
- SMTP email account for notifications

## Setup

1. **Clone/Download the project files**

2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:
   ```env
   # Oracle IDCS Credentials
   ORACLE_USERNAME=AGENT_TEST
   ORACLE_PASSWORD=Automation@123

   # Email Configuration (Required)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   EMAIL_TO=p.harshith.kumar@accenture.com

   # Optional: Adjust thresholds
   CHECK_INTERVAL_MINUTES=30
   STUCK_PROCESS_THRESHOLD_MINUTES=20
   ALL_CLEAR_INTERVAL_HOURS=1
   ```

3. **For Gmail SMTP**: Enable 2-factor authentication and create an App Password

## Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f cfao-monitor

# Stop the agent
docker-compose down
```

### Option 2: Direct Python Execution

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Run once for testing
python Agent.py --once

# Run scheduled (production)
python Agent.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ORACLE_USERNAME` | AGENT_TEST | Oracle IDCS username |
| `ORACLE_PASSWORD` | Automation@123 | Oracle IDCS password |
| `LOGIN_URL` | Oracle IDCS URL | Login page URL |
| `CFAO_PROCESSES_URL` | CFAO processes URL | Open processes page URL |
| `SMTP_HOST` | - | SMTP server hostname |
| `SMTP_PORT` | 587 | SMTP server port |
| `SMTP_USER` | - | SMTP username |
| `SMTP_PASSWORD` | - | SMTP password/app password |
| `EMAIL_TO` | p.harshith.kumar@accenture.com | Alert recipient email |
| `CHECK_INTERVAL_MINUTES` | 30 | Monitoring interval |
| `STUCK_PROCESS_THRESHOLD_MINUTES` | 20 | Stuck process threshold |
| `ALL_CLEAR_INTERVAL_HOURS` | 1 | All-clear notification interval |
| `BROWSER_HEADLESS` | true | Run browser in headless mode |
| `STATE_FILE` | state.json | State persistence file |
| `LOG_FILE` | agent.log | Log file location |

## Operation

### Monitoring Cycle

1. **Login**: Authenticates with Oracle IDCS
2. **Navigate**: Goes to CFAO open processes page
3. **Refresh**: Clicks refresh button to get latest data
4. **Extract**: Parses process table for all open processes
5. **Analyze**: Checks for processes >20 minutes
6. **Alert**: Sends immediate email for stuck processes
7. **All-Clear**: Sends hourly reassurance when healthy
8. **Sleep**: Waits 30 minutes for next cycle

### Process Data Fields

The agent extracts:
- Description
- Process ID
- Log ID
- Server
- State
- Time (elapsed duration)
- Locks (if available)

### Notifications

#### Stuck Process Alert
- **Trigger**: Any process >20 minutes
- **Frequency**: Every 30 minutes if issue persists
- **Content**: Process details, elapsed time, server info

#### All-Clear Notification
- **Trigger**: No stuck processes + 1 hour since last all-clear
- **Frequency**: Maximum once per hour
- **Content**: Reassurance message with timestamp

## Monitoring & Troubleshooting

### Logs
```bash
# View recent logs
tail -f logs/agent.log

# View Docker logs
docker-compose logs -f cfao-monitor
```

### Health Check
```bash
# Check if container is running
docker-compose ps

# Check agent health
docker-compose exec cfao-monitor python -c "print('Agent is running')"
```

### Common Issues

1. **Login Failures**
   - Verify Oracle credentials
   - Check network connectivity
   - Review browser automation logs

2. **Email Not Sending**
   - Verify SMTP settings
   - Check Gmail app password
   - Review email server logs

3. **No Process Data**
   - Check CFAO page structure changes
   - Verify refresh button functionality
   - Review table parsing logic

### Testing

Run a single cycle for testing:
```bash
python Agent.py --once
```

This will perform one complete monitoring cycle without scheduling.

## Security Considerations

- Store `.env` file securely (not in version control)
- Use app passwords for Gmail instead of main password
- Consider using Docker secrets for production deployment
- Regularly rotate Oracle and email credentials
- Monitor logs for sensitive data exposure

## Architecture

- **Agent.py**: Main application logic
- **config.py**: Configuration management
- **state.json**: Persistent state storage
- **Docker**: Containerized deployment
- **APScheduler**: Internal scheduling
- **Playwright**: Browser automation
- **SMTP**: Email notifications

## License

This project is proprietary. All rights reserved.