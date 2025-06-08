#!/usr/bin/env python3
import subprocess
import csv
import re

PASSWD_FILE = '/etc/passwd'
OUTPUT_FILE = '2025-06-08_user_login_report.csv'

# Step 1: Parse /etc/passwd
accounts = []
with open(PASSWD_FILE, 'r') as f:
    for line in f:
        if line.strip() == '' or line.startswith('#'):
            continue
        parts = line.strip().split(':')
        if len(parts) < 7:
            continue
        username, _, uid, _, _, _, shell = parts
        try:
            uid_num = int(uid)
        except ValueError:
            uid_num = -9999
        accounts.append({
            'username': username,
            'uid': uid_num,
            'shell': shell
        })

# Step 2: Run 'last' and parse output
last_output = subprocess.run(['last'], capture_output=True, text=True).stdout
last_logins = {}
for line in last_output.splitlines():
    if not line or line.startswith('reboot') or line.startswith('shutdown') or line.startswith('wtmp begins'):
        continue
    # Example: ekansh     console    Mon  3 Mar 00:39 - 23:16 (53+22:36)
    m = re.match(r'^(\S+)\s+', line)
    if m:
        user = m.group(1)
        if user not in last_logins:
            # Only record most recent
            last_logins[user] = line

# Step 3: Determine account type & last login
rows = []
for acc in accounts:
    username = acc['username']
    uid = acc['uid']
    shell = acc['shell']
    if shell.endswith('false') or shell.endswith('nologin') or uid < 0 or (uid < 500 and username != 'root'):
        acc_type = 'System/Service'
    else:
        acc_type = 'Real User'
    last_login = last_logins.get(username, '')
    if last_login:
        # Extract login date/time
        parts = last_login.split()
        if len(parts) > 4:
            last_login_str = ' '.join(parts[2:7])
        else:
            last_login_str = last_login
    else:
        last_login_str = ''
    rows.append([username, uid, acc_type, last_login_str])

# Step 4: Write CSV output
with open(OUTPUT_FILE, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Username', 'UID', 'Account Type', 'Last Login'])
    for row in rows:
        writer.writerow(row)

print(f"User login report saved to {OUTPUT_FILE}")