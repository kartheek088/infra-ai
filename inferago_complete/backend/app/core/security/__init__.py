"""
Security module — Phase 2 (detection) + auth crypto.

Re-exports both deterministic security detection (detectors, patterns) and the
authentication helper functions (hash_password, verify_password, create_access_token).
"""
from dataclasses import dataclass, field
from typing import Optional
import re

from app.adapters.base_adapter import StandardExecution, NodeExecution

# ── auth crypto helpers (re-exported for backward compat) ─────────────────────────
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ── result type ────────────────────────────────────────────────────────────────

@dataclass
class SecurityFindingResult:
    detector_id:    str
    detector_name:  str
    severity:       str          # critical | high | medium | low | info
    title:          str
    confidence:     float = 1.0  # 0.0–1.0
    description:    Optional[str] = None
    finding_data:   dict = field(default_factory=dict)
    node_name:      Optional[str] = None
    provider:       Optional[str] = None

    # Risk scoring inputs (consumed by RiskScorer)
    risk_factors:   list[dict] = field(default_factory=list)


# ── Sensitivity data patterns ─────────────────────────────────────────────────

PII_PATTERNS = {
    "ssn":        (r"\b\d{3}-\d{2}-\d{4}\b",                  "Social Security Number"),
    "credit_card":(r"\b(?:\d{4}[-\s]?){3}\d{4}\b",            "Credit Card Number"),
    "email":      (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b", "Email Address"),
    "phone":      (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "Phone Number"),
    "ip_address": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",             "IP Address"),
}

SECRET_PATTERNS = {
    "api_key":       (r"(?i)(api[_-]?key|apikey|api_secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{16,})['\"]?", "API Key"),
    # OpenAI / LLM provider keys: sk_live_xxx, sk_test_xxx (common in LLM outputs/inputs)
    # Min 16 chars after sk_live_/sk_test_ to match actual key lengths
    "openai_key":    (r"(?i)sk_(?:live|test|prod)[A-Za-z0-9_\-]{16,}",                                   "OpenAI/LLM API Key"),
    "bearer_token":  (r"(?i)bearer\s+[A-Za-z0-9_\-\.]+",                                       "Bearer Token"),
    "aws_key":       (r"(?i)(AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",         "AWS Access Key"),
    "aws_secret":    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?", "AWS Secret Key"),
    "private_key":   (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",                  "Private Key"),
    "github_token":  (r"(?i)gh[pousr]_[A-Za-z0-9_]{36,}",                                        "GitHub Token"),
    "slack_token":   (r"(?i)xox[baprs]-\d+-[A-Za-z0-9]+",                                        "Slack Token"),
    "password_field":(r"(?i)password\s*[:=]\s*['\"][^'\"]{8,}['\"]",                             "Hardcoded Password"),
}

# Suspicious external destinations (domains/IPs to flag)
SUSPICIOUS_DOMAINS = re.compile(
    r"(?i)(pastebin|ghostbin|transfernow|dropmefiles|wetransfer|anonfile|"
    r"mega\.nz|ngrok\.io|tunnel\.py|serveo\.net|localtunnel|pagekite)",
    re.IGNORECASE,
)

INTERNAL_HOSTNAMES = re.compile(
    r"(?i)^(localhost|127\.0\.0\.1|10\.|172\.(1[6-9]|2[0-9]|3[01])\.|"
    r"192\.168\.|::1|fe80:|fd[0-9a-f]{2}:)",
)

# HTTP methods considered risky when sending to external destinations
RISKY_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


# ── helpers ───────────────────────────────────────────────────────────────────

def _scan_text_for_patterns(text: str, pattern_dict: dict) -> list[dict]:
    """Return list of {pattern_name, matched_value} found in text."""
    findings = []
    if not text:
        return findings
    for name, (regex, label) in pattern_dict.items():
        for match in re.finditer(regex, text):
            findings.append({
                "pattern": name,
                "label":   label,
                "value":   match.group(0)[:80],  # truncate for safety
                "offset":  match.start(),
            })
    return findings


def _severity_to_score(severity: str) -> int:
    return {"critical": 100, "high": 75, "medium": 50, "low": 25, "info": 10}.get(severity, 0)


# ── individual detectors ───────────────────────────────────────────────────────

class SensitiveDataExposureDetector:
    """
    Detects PII, credentials, and secrets in node input/output data.
    Scans: prompt text, response text, node metadata, HTTP headers/body.
    """
    detector_id   = "sensitive_data_exposure"
    detector_name = "Sensitive Data Exposure"

    @classmethod
    def detect(cls, execution: StandardExecution, nodes: list[NodeExecution]) -> list[SecurityFindingResult]:
        findings = []

        for node in nodes:
            if node.node_type not in ("llm", "http_request", "transform", "other"):
                continue

            # Build text corpus to scan
            texts = [
                node.metadata.get("prompt", "") if node.metadata else "",
                node.metadata.get("response", "") if node.metadata else "",
                node.metadata.get("input", "") if node.metadata else "",
                node.metadata.get("output", "") if node.metadata else "",
                node.metadata.get("url", "") if node.metadata else "",
                node.metadata.get("headers", "") if node.metadata else "",
                node.metadata.get("body", "") if node.metadata else "",
                str(node.metadata) if node.metadata else "",
            ]
            full_text = " ".join(str(t) for t in texts)

            pii_hits  = _scan_text_for_patterns(full_text, PII_PATTERNS)
            sec_hits  = _scan_text_for_patterns(full_text, SECRET_PATTERNS)

            if sec_hits:
                for hit in sec_hits:
                    severity = "critical" if hit["pattern"] in (
                        "private_key", "aws_secret", "github_token", "password_field"
                    ) else "high"

                    findings.append(SecurityFindingResult(
                        detector_id=cls.detector_id,
                        detector_name=cls.detector_name,
                        severity=severity,
                        confidence=0.98,
                        title=f"Secret/Credential detected in {node.node_name}",
                        description=f"{hit['label']} found in {node.node_name} ({node.node_type}). "
                                    f"Value begins with: {hit['value'][:30]}",
                        finding_data={
                            "node_name":   node.node_name,
                            "node_type":   node.node_type,
                            "pattern":     hit["pattern"],
                            "label":       hit["label"],
                            "matched_val": hit["value"][:40],
                            "provider":    node.provider,
                        },
                        node_name=node.node_name,
                        provider=node.provider,
                        risk_factors=[
                            {"factor": "credential_exposure", "weight": 1.0, "contribution": _severity_to_score(severity)},
                            {"factor": "high_severity_pattern", "weight": 0.5, "contribution": 25 if severity == "critical" else 0},
                            {"factor": "node_type_llm", "weight": 0.3, "contribution": 15 if node.node_type == "llm" else 0},
                        ],
                    ))

            if pii_hits:
                for hit in pii_hits:
                    findings.append(SecurityFindingResult(
                        detector_id="pii_exposure",
                        detector_name="PII Exposure",
                        severity="medium",
                        confidence=0.95,
                        title=f"PII detected in {node.node_name}",
                        description=f"{hit['label']} found in node output. "
                                    f"This may violate data privacy requirements.",
                        finding_data={
                            "node_name": node.node_name,
                            "pattern":   hit["pattern"],
                            "label":     hit["label"],
                            "provider":  node.provider,
                        },
                        node_name=node.node_name,
                        provider=node.provider,
                        risk_factors=[
                            {"factor": "pii_in_output", "weight": 1.0, "contribution": 40},
                            {"factor": "privacy_violation_risk", "weight": 0.5, "contribution": 20},
                        ],
                    ))

        return findings


class APISecretLeakDetector:
    """
    Detects hardcoded API keys, tokens, and secrets in workflow data.
    Scans all node metadata and event messages.
    """
    detector_id   = "api_secret_leak"
    detector_name = "API Secret Leak"

    @classmethod
    def detect(cls, execution: StandardExecution, nodes: list[NodeExecution]) -> list[SecurityFindingResult]:
        findings = []

        all_texts = [ev.message or "" for ev in (execution.events or [])]
        for node in nodes:
            if node.metadata:
                all_texts.append(str(node.metadata))

        full_text = " ".join(all_texts)
        hits = _scan_text_for_patterns(full_text, SECRET_PATTERNS)

        for hit in hits:
            severity = "critical" if hit["pattern"] in ("private_key", "aws_secret", "github_token") else "high"
            findings.append(SecurityFindingResult(
                detector_id=cls.detector_id,
                detector_name=cls.detector_name,
                severity=severity,
                confidence=0.99,
                title=f"API Secret leak detected",
                description=f"{hit['label']} found in execution data. "
                            f"Value begins: {hit['value'][:30]}. "
                            f"This secret may be logged or stored in plain text.",
                finding_data={
                    "pattern":     hit["pattern"],
                    "label":      hit["label"],
                    "matched_val": hit["value"][:60],
                    "platform":   execution.platform,
                },
                risk_factors=[
                    {"factor": "secret_exposure", "weight": 1.0, "contribution": _severity_to_score(severity)},
                    {"factor": "lateral_movement_risk", "weight": 0.7, "contribution": 30},
                ],
            ))

        return findings


class ExternalDataExfiltrationDetector:
    """
    Detects HTTP requests from LLM nodes to suspicious external destinations.
    Flags: ngrok tunnels, paste sites, file sharing, unusual CDNs.
    """
    detector_id   = "external_data_exfiltration"
    detector_name = "External Data Exfiltration"

    @classmethod
    def detect(cls, execution: StandardExecution, nodes: list[NodeExecution]) -> list[SecurityFindingResult]:
        findings = []

        for node in nodes:
            if node.node_type not in ("llm", "http_request"):
                continue

            url = (node.metadata.get("url", "") if node.metadata else "") or ""
            if not url:
                continue

            # Check for suspicious external destinations
            if SUSPICIOUS_DOMAINS.search(url):
                findings.append(SecurityFindingResult(
                    detector_id=cls.detector_id,
                    detector_name=cls.detector_name,
                    severity="critical",
                    confidence=0.97,
                    title=f"Suspicious external destination from {node.node_name}",
                    description=f"LLM output or HTTP request to '{url}'. "
                                f"This may indicate data exfiltration via tunnels or paste sites.",
                    finding_data={
                        "node_name": node.node_name,
                        "url":       url,
                        "method":    node.metadata.get("method", "GET") if node.metadata else "GET",
                        "provider":  node.provider,
                    },
                    node_name=node.node_name,
                    provider=node.provider,
                    risk_factors=[
                        {"factor": "external_exfil", "weight": 1.0, "contribution": 100},
                        {"factor": "tunnel_service", "weight": 0.8, "contribution": 40},
                        {"factor": "data_leak_risk", "weight": 1.0, "contribution": 50},
                    ],
                ))

            # Check for HTTP requests from LLM nodes to non-internal destinations
            method = (node.metadata.get("method", "GET") if node.metadata else "GET") or "GET"
            if node.node_type == "llm" and method.upper() in RISKY_HTTP_METHODS:
                if not INTERNAL_HOSTNAMES.search(url) and not url.startswith("https://api.openai") \
                   and not url.startswith("https://api.anthropic") and not url.startswith("https://generativelanguage"):
                    findings.append(SecurityFindingResult(
                        detector_id="llm_http_risk",
                        detector_name="LLM HTTP Request Risk",
                        severity="medium",
                        confidence=0.85,
                        title=f"LLM making HTTP {method} to external URL",
                        description=f"Node {node.node_name} is making a {method} request to {url}. "
                                    f"Review whether this is intentional.",
                        finding_data={
                            "node_name": node.node_name,
                            "url":       url,
                            "method":    method,
                            "provider":  node.provider,
                        },
                        node_name=node.node_name,
                        provider=node.provider,
                        risk_factors=[
                            {"factor": "llm_http_risk", "weight": 1.0, "contribution": 45},
                            {"factor": "non_standard_destination", "weight": 0.6, "contribution": 20},
                        ],
                    ))

        return findings


class ModelAnomalyDetector:
    """
    Detects anomalous model usage: unknown providers, unusual model names,
    very high token counts (potential abuse), or cost anomalies.
    """
    detector_id   = "model_anomaly"
    detector_name = "Model Usage Anomaly"

    @classmethod
    def detect(cls, execution: StandardExecution, nodes: list[NodeExecution]) -> list[SecurityFindingResult]:
        findings = []

        KNOWN_PROVIDERS = {"openai", "anthropic", "google", "azure", "mistral", "cohere", "unknown"}

        for node in nodes:
            if node.node_type != "llm":
                continue

            provider = (node.provider or "").lower()
            model    = (node.model or "").lower()

            # Unknown provider
            if provider not in KNOWN_PROVIDERS and provider != "custom":
                findings.append(SecurityFindingResult(
                    detector_id=cls.detector_id,
                    detector_name=cls.detector_name,
                    severity="low",
                    confidence=0.6,
                    title=f"Unknown model provider: {provider}",
                    description=f"Model from provider '{provider}' is not in the recognized list. "
                                f"Verify this is intentional.",
                    finding_data={
                        "node_name": node.node_name,
                        "provider":  node.provider,
                        "model":     node.model,
                    },
                    node_name=node.node_name,
                    provider=node.provider,
                    risk_factors=[
                        {"factor": "unknown_provider", "weight": 1.0, "contribution": 20},
                    ],
                ))

            # Very high token count (potential abuse or infinite loop)
            if node.total_tokens > 200_000:
                findings.append(SecurityFindingResult(
                    detector_id="token_anomaly",
                    detector_name="Token Count Anomaly",
                    severity="high",
                    confidence=0.9,
                    title=f"Extremely high token count: {node.total_tokens:,}",
                    description=f"Node {node.node_name} processed {node.total_tokens:,} tokens in one execution. "
                                f"This may indicate an infinite loop, abuse, or a misconfigured workflow.",
                    finding_data={
                        "node_name":        node.node_name,
                        "total_tokens":     node.total_tokens,
                        "prompt_tokens":    node.prompt_tokens,
                        "completion_tokens": node.completion_tokens,
                        "provider":         node.provider,
                    },
                    node_name=node.node_name,
                    provider=node.provider,
                    risk_factors=[
                        {"factor": "token_anomaly", "weight": 1.0, "contribution": 70},
                        {"factor": "cost_exposure", "weight": 0.8, "contribution": 40},
                    ],
                ))

        return findings


class ErrorPatternDetector:
    """
    Detects execution errors that may indicate security issues:
    authentication failures, rate limiting, injection attempts.
    """
    detector_id   = "error_pattern"
    detector_name = "Error Pattern Detection"

    @classmethod
    def detect(cls, execution: StandardExecution, nodes: list[NodeExecution]) -> list[SecurityFindingResult]:
        findings = []

        SECURITY_ERROR_PATTERNS = [
            (r"(?i)unauthorized|auth.*fail|invalid.*token|401|403",              "Authentication Failure",    "high"),
            (r"(?i)rate.?limit|429|too.?many.?request",                           "Rate Limit Hit",             "medium"),
            (r"(?i)sql.*inject|xss|csrf|injection|sanitize",                     "Injection Pattern Detected", "high"),
            (r"(?i)prompt.?inject|system.?prompt.?leak|jailbreak",               "Prompt Injection",           "critical"),
            (r"(?i)timeout|timed?.?out|504|503|gateway.?timeout",                  "Service Timeout",           "low"),
            (r"(?i)access.?denied|permission.?denied|forbidden|permission.?error","Permission Error",         "medium"),
        ]

        for node in nodes:
            err = (node.error_message or "").strip()
            if not err:
                continue

            for pattern, label, severity in SECURITY_ERROR_PATTERNS:
                if re.search(pattern, err):
                    findings.append(SecurityFindingResult(
                        detector_id=cls.detector_id,
                        detector_name=cls.detector_name,
                        severity=severity,
                        confidence=0.9 if severity == "critical" else 0.85,
                        title=f"Security-relevant error: {label}",
                        description=f"Node {node.node_name} error matching '{label}': {err[:200]}",
                        finding_data={
                            "node_name":  node.node_name,
                            "error_msg":  err[:500],
                            "label":      label,
                            "provider":   node.provider,
                        },
                        node_name=node.node_name,
                        provider=node.provider,
                        risk_factors=[
                            {"factor": f"error_{label.lower().replace(' ', '_')}", "weight": 1.0, "contribution": _severity_to_score(severity)},
                        ],
                    ))

        return findings


# ── All detectors registry ─────────────────────────────────────────────────────

ALL_DETECTORS: list = [
    SensitiveDataExposureDetector,
    APISecretLeakDetector,
    ExternalDataExfiltrationDetector,
    ModelAnomalyDetector,
    ErrorPatternDetector,
]
