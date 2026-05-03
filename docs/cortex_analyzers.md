# Cortex Analyzers Configuration

> This document describes the configuration of Cortex analyzers for ransomware detection and threat intelligence analysis in the SOAR laboratory.

## Overview

Cortex analyzers are configured to provide automated analysis of IoCs (Indicators of Compromise) extracted from ransomware alerts. The configuration focuses on free, reliable analyzers that can operate within the constraints of a laboratory environment.

## Enabled Analyzers

### 1. HashInfo
- **Purpose**: Basic file hash information and metadata
- **Input**: SHA256, MD5, SHA1 hashes
- **Output**: File type, size, basic metadata
- **Configuration**: No external API required
- **Timeout**: 30 seconds
- **Retries**: 1

### 2. VirusTotal
- **Purpose**: Multi-engine antivirus scanning
- **Input**: File hashes, URLs, IPs, domains
- **Output**: Detection ratio, scan results, last seen
- **Configuration**: Requires VirusTotal API key
- **Timeout**: 60 seconds
- **Retries**: 1
- **Rate Limit**: 4 requests/minute (free tier)

### 3. URLHaus
- **Purpose**: Malware URL tracking
- **Input**: URLs, domains, IPs, file hashes
- **Output**: Malware family, first seen, tags
- **Configuration**: Free public API
- **Timeout**: 30 seconds
- **Retries**: 1

### 4. PassiveTotal
- **Purpose**: Passive DNS and threat intelligence
- **Input**: Domains, IPs, hashes
- **Output**: DNS history, malware associations
- **Configuration**: Requires free API key
- **Timeout**: 45 seconds
- **Retries**: 1

### 5. MISP
- **Purpose**: Threat intelligence sharing
- **Input**: All IoC types
- **Output**: Related events, tags, IoC context
- **Configuration**: Local or public MISP instance
- **Timeout**: 30 seconds
- **Retries**: 1

## Configuration Files

### Main Cortex Configuration
```yaml
# /etc/cortex/application.conf
analyzer {
  # HashInfo analyzer
  "HashInfo_1_0" {
    name = "HashInfo"
    configuration = {
      # No configuration required
    }
  }
  
  # VirusTotal analyzer
  "VirusTotal_2_0" {
    name = "VirusTotal"
    configuration = {
      key = "${VIRUSTOTAL_API_KEY}"
      "max_tlp" = 2
    }
  }
  
  # URLHaus analyzer
  "URLHaus_1_0" {
    name = "URLHaus"
    configuration = {
      # No configuration required for public API
    }
  }
  
  # PassiveTotal analyzer
  "PassiveTotal_1_0" {
    name = "PassiveTotal"
    configuration = {
      key = "${PASSIVETOTAL_API_KEY}"
    }
  }
}
```

## Analyzer Workflows

### Ransomware Detection Workflow
1. **Hash Analysis**: Run HashInfo + VirusTotal on file hash
2. **Network Analysis**: Run URLHaus + PassiveTotal on IPs/domains
3. **Threat Intel**: Query MISP for related IoCs
4. **Score Calculation**: Combine results for final threat score

### Scoring Logic
- **VirusTotal Detection**: 0-40 points (based on detection ratio)
- **URLHaus Match**: 0-30 points
- **PassiveTotal Malware**: 0-20 points
- **MISP Threat**: 0-10 points

**Thresholds:**
- **0-30**: Low risk (Benign)
- **31-60**: Medium risk (Suspicious)
- **61-100**: High risk (Malicious)

## Performance Optimization

### Concurrency Limits
- **Max concurrent analyzers**: 3
- **Queue size**: 50
- **Worker threads**: 2

### Timeout Configuration
- **Hash analyzers**: 30 seconds
- **Network analyzers**: 60 seconds
- **Threat intel**: 45 seconds

### Retry Strategy
- **Network errors**: 1 retry after 5 seconds
- **API limits**: Exponential backoff
- **Timeouts**: No retry for security

## Testing Procedures

### Test Hashes
```bash
# Benign hash
echo "d41d8cd98f00b204e9800998ecf8427e" | python3 -c "
import sys, json, requests
hash_value = sys.stdin.read().strip()
payload = {
    'analyzer': 'HashInfo',
    'input': {'type': 'hash', 'value': hash_value}
}
response = requests.post('http://localhost:9001/api/analyzers/run', 
                       json=payload, 
                       headers={'Authorization': 'Bearer YOUR_API_KEY'})
print(json.dumps(response.json(), indent=2))
"

# Malicious hash (example)
echo "44d88612fea8a8f36de82e1278abb02f" | python3 -c "
import sys, json, requests
hash_value = sys.stdin.read().strip()
payload = {
    'analyzer': 'VirusTotal_2_0',
    'input': {'type': 'hash', 'value': hash_value}
}
response = requests.post('http://localhost:9001/api/analyzers/run', 
                       json=payload, 
                       headers={'Authorization': 'Bearer YOUR_API_KEY'})
print(json.dumps(response.json(), indent=2))
"
```

### Test IPs
```bash
# Test malicious IP
curl -X POST http://localhost:9001/api/analyzers/run \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "analyzer": "URLHaus_1_0",
    "input": {
      "type": "ip",
      "value": "185.220.101.182"
    }
  }'
```

## Monitoring and Logging

### Metrics to Track
- **Analyzer execution time**
- **Success/failure rate**
- **API quota usage**
- **Queue depth**

### Log Configuration
```yaml
# Enable detailed logging
logger {
  level = "INFO"
  format = "json"
  appenders = ["file", "console"]
}
```

## Security Considerations

### API Key Management
- Store API keys in environment variables
- Rotate keys every 90 days
- Monitor API usage for anomalies
- Use least privilege principle

### Data Privacy
- Set TLP (Traffic Light Protocol) appropriately
- Don't submit sensitive hashes to public APIs
- Consider privacy implications of IoC sharing

## Troubleshooting

### Common Issues
1. **API Rate Limits**: Reduce concurrent requests
2. **Network Timeouts**: Increase timeout values
3. **Invalid API Keys**: Verify key validity and permissions
4. **Memory Issues**: Limit concurrent analyzer jobs

### Debug Commands
```bash
# Check analyzer status
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9001/api/analyzer

# Check job status
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9001/api/job/JOB_ID

# View system health
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9001/api/health
```

## Maintenance

### Regular Tasks
- **Weekly**: Review analyzer performance metrics
- **Monthly**: Update analyzer definitions
- **Quarterly**: Rotate API keys and review permissions
- **Annually**: Evaluate new analyzers and retire unused ones

### Backup Strategy
- Backup analyzer configurations
- Document custom analyzer settings
- Maintain API key inventory