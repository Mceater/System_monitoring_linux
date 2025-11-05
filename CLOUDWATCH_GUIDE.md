# CloudWatch Integration Guide

## What is CloudWatch?

**AWS CloudWatch** is a monitoring and observability service that collects and tracks metrics, logs, and events from your AWS resources and applications. In this project, CloudWatch is used to **export your system monitoring data** to AWS so you can:

- 📊 **View historical data** - See how your system performed over days/weeks
- 📈 **Create dashboards** - Visualize metrics in graphs and charts
- 🔔 **Set up alarms** - Get notified when CPU/memory exceeds thresholds
- 🌐 **Monitor multiple servers** - Track all your servers from one place
- 📝 **Keep permanent records** - Store metrics for compliance/analysis

## How It Works in This Project

The monitoring tool collects local system metrics (CPU, memory, disk, network) and **automatically sends them to CloudWatch every 60 seconds** when enabled. The metrics are stored in AWS and can be viewed in the CloudWatch console.

### Metrics Sent to CloudWatch:

1. **CPUUtilization** - Overall CPU usage percentage
2. **MemoryUtilization** - Memory usage percentage  
3. **DiskUtilization** - Disk usage for each device/mountpoint
4. **NetworkBytesSent** - Total network bytes sent
5. **NetworkBytesReceived** - Total network bytes received

## Prerequisites

1. **AWS Account** - You need an AWS account (free tier works)
2. **AWS Credentials** - Access key ID and secret access key
3. **IAM Permissions** - User/role needs `cloudwatch:PutMetricData` permission

## Setup Instructions

### Option 1: Using the Setup Script (Recommended)

```bash
cd /Users/kasfiaparvez/system-monitor
./cloudwatch_setup.sh
```

This script will:
- Check if AWS CLI is installed (install if needed)
- Verify/configure AWS credentials
- Test CloudWatch connectivity

### Option 2: Manual Setup

1. **Install AWS CLI** (if not installed):
   ```bash
   # macOS
   brew install awscli
   
   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **Configure AWS Credentials**:
   ```bash
   aws configure
   ```
   
   You'll be prompted for:
   - **AWS Access Key ID**: Your AWS access key
   - **AWS Secret Access Key**: Your AWS secret key
   - **Default region name**: e.g., `us-east-1`
   - **Default output format**: `json` (recommended)

3. **Get AWS Credentials** (if you don't have them):
   - Go to AWS Console → IAM → Users → Your User → Security Credentials
   - Create Access Key
   - Download the credentials file

4. **Set IAM Permissions**:
   Your AWS user needs this permission:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "cloudwatch:PutMetricData"
               ],
               "Resource": "*"
           }
       ]
   }
   ```

## Using CloudWatch with the Monitor

### Basic Usage

```bash
# Run monitor with CloudWatch enabled
python3 monitor.py --cloudwatch
```

### Custom Region

```bash
# Use a different AWS region
python3 monitor.py --cloudwatch --region us-west-2
```

### Custom Namespace

```bash
# Use a custom namespace (helps organize metrics)
python3 monitor.py --cloudwatch --namespace MyServerMonitor
```

### All Options

```bash
python3 monitor.py --cloudwatch --region us-east-1 --namespace SystemMonitor
```

## Viewing Metrics in CloudWatch

### 1. Access CloudWatch Console

1. Go to [AWS CloudWatch Console](https://console.aws.amazon.com/cloudwatch/)
2. Sign in with your AWS account
3. Navigate to **Metrics** → **All metrics**

### 2. Find Your Metrics

- Look for namespace: `SystemMonitor` (or your custom namespace)
- You'll see metrics like:
  - `CPUUtilization`
  - `MemoryUtilization`
  - `DiskUtilization`
  - `NetworkBytesSent`
  - `NetworkBytesReceived`

### 3. Create a Dashboard

1. Go to **Dashboards** → **Create dashboard**
2. Add widgets for each metric
3. Customize graphs and time ranges
4. Save the dashboard

### 4. Set Up Alarms

1. Go to **Alarms** → **Create alarm**
2. Select a metric (e.g., CPUUtilization)
3. Set threshold (e.g., > 80%)
4. Configure notification (email, SNS topic)
5. Save the alarm

## Example: Setting Up an Alarm

**Scenario**: Alert when CPU usage exceeds 80%

```bash
# In AWS Console:
# 1. CloudWatch → Alarms → Create alarm
# 2. Select metric: SystemMonitor → CPUUtilization
# 3. Statistic: Average
# 4. Period: 5 minutes
# 5. Threshold: Greater than 80
# 6. Add notification (your email)
# 7. Create alarm
```

## Cost Considerations

- **Free Tier**: First 1 million API requests/month free
- **After Free Tier**: ~$0.01 per 1,000 metric requests
- **This tool**: Sends ~5 metrics every 60 seconds = ~7,200 metrics/day
- **Monthly cost**: Approximately $0.20-0.50/month (very affordable)

## Troubleshooting

### "CloudWatch credentials not found"

**Solution**: Configure AWS credentials
```bash
aws configure
```

### "CloudWatch initialization failed"

**Causes**:
- Invalid credentials
- Network connectivity issues
- Missing IAM permissions

**Solution**: 
1. Verify credentials: `aws sts get-caller-identity`
2. Check IAM permissions for `cloudwatch:PutMetricData`
3. Verify network connectivity to AWS

### Metrics Not Appearing in CloudWatch

**Wait time**: Metrics may take 1-2 minutes to appear
**Check**: 
- Verify namespace matches (default: `SystemMonitor`)
- Check CloudWatch region matches your configured region
- Ensure monitor is running with `--cloudwatch` flag

### Monitor Continues Without CloudWatch

If CloudWatch fails, the monitor **continues running** normally. You'll see a warning message, but local monitoring still works. This ensures the tool is resilient.

## Command Reference

```bash
# Basic monitoring (no CloudWatch)
python3 monitor.py

# With CloudWatch
python3 monitor.py --cloudwatch

# Custom region
python3 monitor.py --cloudwatch --region eu-west-1

# Custom namespace
python3 monitor.py --cloudwatch --namespace ProductionServer

# All options
python3 monitor.py --cloudwatch --region us-east-1 --namespace MyMonitor
```

## Benefits of Using CloudWatch

✅ **Historical Data**: Keep records of system performance over time
✅ **Centralized Monitoring**: Monitor multiple servers from one place
✅ **Alerts**: Get notified of issues automatically
✅ **Dashboards**: Visualize system health at a glance
✅ **Compliance**: Maintain monitoring records for audits
✅ **Scalability**: Monitor hundreds of servers easily

## Next Steps

1. ✅ Set up AWS credentials
2. ✅ Run monitor with `--cloudwatch` flag
3. ✅ Verify metrics appear in CloudWatch console
4. ✅ Create a dashboard for visualization
5. ✅ Set up alarms for critical thresholds

---

**Note**: CloudWatch is optional. The monitor works perfectly fine without it for local monitoring only.

