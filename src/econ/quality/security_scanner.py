"""
経済指標システム セキュリティテスト・脆弱性検査システム
セキュリティベストプラクティス検証とリスク評価機能を提供
"""

import os
import re
import ast
import json
import sqlite3
import hashlib
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

from ..config.settings import get_econ_config


@dataclass
class SecurityVulnerability:
    """セキュリティ脆弱性データ"""
    vuln_id: str
    severity: str  # critical, high, medium, low, info
    category: str
    title: str
    description: str
    file_path: Optional[str]
    line_number: Optional[int]
    code_snippet: Optional[str]
    recommendation: str
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SecurityScanResult:
    """セキュリティスキャン結果"""
    scan_id: str
    scan_type: str
    total_files_scanned: int
    vulnerabilities: List[SecurityVulnerability]
    security_score: float
    risk_level: str
    scan_duration: float
    timestamp: datetime
    metadata: Dict[str, Any]


class SecurityScanner:
    """経済指標システム セキュリティスキャナー"""
    
    def __init__(self, config=None):
        self.config = config or get_econ_config()
        
        # セキュリティ設定
        self.security_config = {
            'scan_directories': ['src/econ', 'tests'],
            'excluded_patterns': ['__pycache__', '.pyc', '.git', 'node_modules'],
            'results_dir': getattr(self.config, 'security_scan_results_dir', 'build/security_scans'),
            'severity_weights': {
                'critical': 10.0,
                'high': 7.5,
                'medium': 5.0,
                'low': 2.5,
                'info': 1.0
            },
            'risk_thresholds': {
                'low': 85.0,
                'medium': 70.0,
                'high': 50.0,
                'critical': 30.0
            }
        }
        
        # データベース初期化
        self.db_path = Path(self.security_config['results_dir']) / 'security_results.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # セキュリティルール定義
        self.security_rules = self._initialize_security_rules()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self) -> None:
        """セキュリティスキャンデータベース初期化"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS security_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT UNIQUE NOT NULL,
                    scan_type TEXT NOT NULL,
                    total_files_scanned INTEGER NOT NULL,
                    security_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    scan_duration REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT NOT NULL,
                    vuln_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    file_path TEXT,
                    line_number INTEGER,
                    code_snippet TEXT,
                    recommendation TEXT NOT NULL,
                    cwe_id TEXT,
                    cvss_score REAL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES security_scans (scan_id)
                );
                
                CREATE TABLE IF NOT EXISTS security_baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    baseline_name TEXT UNIQUE NOT NULL,
                    baseline_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_security_scans_id_time ON security_scans(scan_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_vulnerabilities_scan_severity ON vulnerabilities(scan_id, severity);
                CREATE INDEX IF NOT EXISTS idx_security_baselines_name ON security_baselines(baseline_name);
            """)
    
    def _initialize_security_rules(self) -> Dict[str, Any]:
        """セキュリティルール初期化"""
        return {
            # 認証・認可
            'hardcoded_secrets': {
                'patterns': [
                    # より具体的なパターンに限定
                    r'(password|passwd|pwd|secret|token|api_key)\s*[=:]\s*["\'][A-Za-z0-9]{16,}["\']',
                    r'(aws_access_key_id|aws_secret_access_key)\s*[=:]\s*["\'][A-Za-z0-9]{16,}["\']'
                ],
                'severity': 'critical',
                'category': 'Authentication',
                'cwe_id': 'CWE-798'
            },
            
            # SQLインジェクション
            'sql_injection': {
                'patterns': [
                    r'execute\([^)]*%[^)]*\)',
                    r'cursor\.execute\([^)]*%[^)]*\)',
                    r'conn\.execute\([^)]*%[^)]*\)',
                    r'query\s*=\s*["\'][^"\']*%[^"\']*["\']'
                ],
                'severity': 'high',
                'category': 'Injection',
                'cwe_id': 'CWE-89'
            },
            
            # コマンドインジェクション
            'command_injection': {
                'patterns': [
                    # より具体的で危険なパターンのみ
                    r'os\.system\([^)]*["\'][^"\']*%[^"\']*["\'][^)]*\)',
                    r'subprocess\.(call|run|Popen)\([^)]*shell\s*=\s*True[^)]*%[^)]*\)',
                    r'eval\([^)]*%[^)]*\)',
                    r'exec\([^)]*%[^)]*\)'
                ],
                'severity': 'high',
                'category': 'Injection',
                'cwe_id': 'CWE-78'
            },
            
            # パストラバーサル
            'path_traversal': {
                'patterns': [
                    r'open\([^)]*\.\.[^)]*\)',
                    r'Path\([^)]*\.\.[^)]*\)',
                    r'join\([^)]*\.\.[^)]*\)'
                ],
                'severity': 'medium',
                'category': 'Path Traversal',
                'cwe_id': 'CWE-22'
            },
            
            # 暗号化
            'weak_crypto': {
                'patterns': [
                    # セキュリティクリティカルな用途での使用のみ検出
                    r'hashlib\.md5\([^)]*password[^)]*\)',
                    r'hashlib\.sha1\([^)]*password[^)]*\)',
                    r'DES\([^)]*encrypt[^)]*\)',
                    r'RC4\([^)]*encrypt[^)]*\)',
                    r'random\.random\([^)]*token[^)]*\)'
                ],
                'severity': 'medium',
                'category': 'Cryptography',
                'cwe_id': 'CWE-327'
            },
            
            # ログ・デバッグ情報漏洩
            'information_disclosure': {
                'patterns': [
                    r'print\([^)]*password[^)]*\)',
                    r'logger\.(debug|info|warning)\([^)]*password[^)]*\)',
                    r'traceback\.print_exc\(\)'
                ],
                'severity': 'low',
                'category': 'Information Disclosure',
                'cwe_id': 'CWE-532'
            },
            
            # 不適切なエラーハンドリング
            'error_handling': {
                'patterns': [
                    r'except:\s*pass',
                    r'except Exception:\s*pass',
                    r'except.*:\s*continue'
                ],
                'severity': 'low',
                'category': 'Error Handling',
                'cwe_id': 'CWE-248'
            }
        }
    
    def run_comprehensive_scan(self) -> SecurityScanResult:
        """包括的セキュリティスキャン実行"""
        scan_id = f"comprehensive_{int(datetime.now().timestamp())}"
        start_time = datetime.now()
        
        self.logger.info(f"包括的セキュリティスキャン開始: {scan_id}")
        
        vulnerabilities = []
        files_scanned = 0
        
        # 1. 静的コード解析
        static_vulns, static_files = self._run_static_analysis()
        vulnerabilities.extend(static_vulns)
        files_scanned += static_files
        
        # 2. 依存関係脆弱性チェック
        dependency_vulns = self._check_dependency_vulnerabilities()
        vulnerabilities.extend(dependency_vulns)
        
        # 3. 設定ファイルチェック
        config_vulns, config_files = self._check_configuration_security()
        vulnerabilities.extend(config_vulns)
        files_scanned += config_files
        
        # 4. 環境変数・シークレット検査
        secret_vulns = self._check_secrets_exposure()
        vulnerabilities.extend(secret_vulns)
        
        # 5. ネットワーク設定チェック
        network_vulns = self._check_network_security()
        vulnerabilities.extend(network_vulns)
        
        # スキャン結果集計
        scan_duration = (datetime.now() - start_time).total_seconds()
        security_score = self._calculate_security_score(vulnerabilities)
        risk_level = self._determine_risk_level(security_score)
        
        scan_result = SecurityScanResult(
            scan_id=scan_id,
            scan_type='comprehensive',
            total_files_scanned=files_scanned,
            vulnerabilities=vulnerabilities,
            security_score=security_score,
            risk_level=risk_level,
            scan_duration=scan_duration,
            timestamp=start_time,
            metadata={
                'static_analysis_files': static_files,
                'config_files': config_files,
                'vulnerability_categories': self._get_vulnerability_categories(vulnerabilities),
                'severity_distribution': self._get_severity_distribution(vulnerabilities)
            }
        )
        
        # データベース保存
        self._save_scan_result(scan_result)
        
        self.logger.info(f"セキュリティスキャン完了: スコア={security_score:.1f}, リスクレベル={risk_level}")
        
        return scan_result
    
    def _run_static_analysis(self) -> Tuple[List[SecurityVulnerability], int]:
        """静的コード解析"""
        vulnerabilities = []
        files_scanned = 0
        
        for scan_dir in self.security_config['scan_directories']:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                continue
            
            for py_file in scan_path.rglob('*.py'):
                # 除外パターンチェック
                if any(pattern in str(py_file) for pattern in self.security_config['excluded_patterns']):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # セキュリティルールチェック
                    file_vulns = self._scan_file_content(str(py_file), content)
                    vulnerabilities.extend(file_vulns)
                    files_scanned += 1
                    
                except Exception as e:
                    self.logger.warning(f"ファイル解析エラー {py_file}: {e}")
        
        return vulnerabilities, files_scanned
    
    def _scan_file_content(self, file_path: str, content: str) -> List[SecurityVulnerability]:
        """ファイル内容のセキュリティスキャン"""
        vulnerabilities = []
        lines = content.split('\n')
        
        for rule_name, rule_config in self.security_rules.items():
            for pattern in rule_config['patterns']:
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        vuln = SecurityVulnerability(
                            vuln_id=f"{rule_name}_{hashlib.md5(f'{file_path}:{line_num}:{match.group()}'.encode()).hexdigest()[:8]}",
                            severity=rule_config['severity'],
                            category=rule_config['category'],
                            title=f"{rule_name.replace('_', ' ').title()} Detected",
                            description=f"Potential security vulnerability found: {match.group()}",
                            file_path=file_path,
                            line_number=line_num,
                            code_snippet=line.strip(),
                            recommendation=self._get_recommendation(rule_name),
                            cwe_id=rule_config.get('cwe_id'),
                            cvss_score=self._get_cvss_score(rule_config['severity'])
                        )
                        vulnerabilities.append(vuln)
        
        return vulnerabilities
    
    def _check_dependency_vulnerabilities(self) -> List[SecurityVulnerability]:
        """依存関係脆弱性チェック"""
        vulnerabilities = []
        
        # requirements.txt チェック
        requirements_file = Path('requirements.txt')
        if requirements_file.exists():
            try:
                # safety パッケージを使用した脆弱性チェック（もしインストールされていれば）
                result = subprocess.run(
                    ['python', '-m', 'pip', 'list', '--format=json'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    installed_packages = json.loads(result.stdout)
                    
                    # 既知の脆弱なパッケージ・バージョンのチェック
                    vulnerable_packages = {
                        'requests': {'versions': ['<2.20.0'], 'cve': 'CVE-2018-18074'},
                        'urllib3': {'versions': ['<1.24.2'], 'cve': 'CVE-2019-11324'},
                        'jinja2': {'versions': ['<2.11.3'], 'cve': 'CVE-2020-28493'}
                    }
                    
                    for package in installed_packages:
                        package_name = package['name'].lower()
                        package_version = package['version']
                        
                        if package_name in vulnerable_packages:
                            vuln_info = vulnerable_packages[package_name]
                            
                            # バージョンチェック（簡易実装）
                            for vuln_version in vuln_info['versions']:
                                if vuln_version.startswith('<'):
                                    # 簡易バージョン比較
                                    min_version = vuln_version[1:]
                                    if self._version_compare(package_version, min_version) < 0:
                                        vuln = SecurityVulnerability(
                                            vuln_id=f"dep_{package_name}_{vuln_info['cve']}",
                                            severity='high',
                                            category='Dependency',
                                            title=f"Vulnerable Dependency: {package_name}",
                                            description=f"Package {package_name} version {package_version} has known vulnerabilities",
                                            file_path='requirements.txt',
                                            line_number=None,
                                            code_snippet=f"{package_name}=={package_version}",
                                            recommendation=f"Update {package_name} to version {min_version} or later",
                                            cwe_id='CWE-1104',
                                            cvss_score=7.5
                                        )
                                        vulnerabilities.append(vuln)
                        
            except Exception as e:
                self.logger.warning(f"依存関係チェックエラー: {e}")
        
        return vulnerabilities
    
    def _check_configuration_security(self) -> Tuple[List[SecurityVulnerability], int]:
        """設定ファイルセキュリティチェック"""
        vulnerabilities = []
        files_checked = 0
        
        config_files = [
            '.env', '.env.example', 'config.json', 'settings.py',
            'app_config.py', 'pyproject.toml', 'setup.py'
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                files_checked += 1
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 機密情報の平文保存チェック
                    sensitive_patterns = [
                        r'(password|passwd|secret|key|token)\s*[=:]\s*[^#\n]+',
                        r'(database|db)_.*[=:]\s*[^#\n]+',
                        r'(api_key|access_key|secret_key)\s*[=:]\s*[^#\n]+'
                    ]
                    
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        for pattern in sensitive_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                # .env.example は除外
                                if config_file != '.env.example':
                                    vuln = SecurityVulnerability(
                                        vuln_id=f"config_sensitive_{config_file}_{line_num}",
                                        severity='medium',
                                        category='Configuration',
                                        title='Sensitive Data in Configuration',
                                        description='Potential sensitive information found in configuration file',
                                        file_path=str(config_path),
                                        line_number=line_num,
                                        code_snippet=line.strip(),
                                        recommendation='Move sensitive data to environment variables or secure storage',
                                        cwe_id='CWE-200',
                                        cvss_score=5.0
                                    )
                                    vulnerabilities.append(vuln)
                    
                    # ファイル権限チェック（Unix系）
                    if hasattr(os, 'stat'):
                        try:
                            file_stat = config_path.stat()
                            file_mode = oct(file_stat.st_mode)[-3:]
                            
                            # 他のユーザーが読み取り可能な場合は警告
                            if file_mode[2] in ['4', '5', '6', '7']:
                                vuln = SecurityVulnerability(
                                    vuln_id=f"config_permissions_{config_file}",
                                    severity='low',
                                    category='Configuration',
                                    title='Insecure File Permissions',
                                    description=f'Configuration file has world-readable permissions: {file_mode}',
                                    file_path=str(config_path),
                                    line_number=None,
                                    code_snippet=None,
                                    recommendation='Restrict file permissions to owner only (chmod 600)',
                                    cwe_id='CWE-732',
                                    cvss_score=2.0
                                )
                                vulnerabilities.append(vuln)
                        except Exception:
                            pass  # 権限チェック失敗は無視
                            
                except Exception as e:
                    self.logger.warning(f"設定ファイル解析エラー {config_file}: {e}")
        
        return vulnerabilities, files_checked
    
    def _check_secrets_exposure(self) -> List[SecurityVulnerability]:
        """シークレット漏洩チェック"""
        vulnerabilities = []
        
        # 環境変数チェック
        sensitive_env_vars = [
            'AWS_SECRET_ACCESS_KEY', 'DATABASE_PASSWORD', 'API_KEY',
            'SECRET_KEY', 'PRIVATE_KEY', 'TOKEN'
        ]
        
        for env_var in os.environ:
            if any(sensitive in env_var.upper() for sensitive in sensitive_env_vars):
                value = os.environ[env_var]
                
                # 値が設定されており、デフォルト値でない場合
                if value and value not in ['your_key_here', 'changeme', 'default', '']:
                    vuln = SecurityVulnerability(
                        vuln_id=f"env_exposure_{env_var}",
                        severity='info',
                        category='Environment',
                        title='Sensitive Environment Variable',
                        description=f'Sensitive environment variable detected: {env_var}',
                        file_path=None,
                        line_number=None,
                        code_snippet=f'{env_var}={value[:10]}...',
                        recommendation='Ensure environment variables are properly secured and not logged',
                        cwe_id='CWE-200',
                        cvss_score=1.0
                    )
                    vulnerabilities.append(vuln)
        
        return vulnerabilities
    
    def _check_network_security(self) -> List[SecurityVulnerability]:
        """ネットワークセキュリティチェック"""
        vulnerabilities = []
        
        # Pythonコード内のネットワーク設定チェック
        network_patterns = {
            'http_usage': {
                'pattern': r'http://[^"\'\s]+',
                'severity': 'low',
                'description': 'HTTP URL detected (should use HTTPS)'
            },
            'ssl_verify_false': {
                'pattern': r'verify\s*=\s*False',
                'severity': 'medium',
                'description': 'SSL certificate verification disabled'
            },
            'debug_server': {
                'pattern': r'debug\s*=\s*True',
                'severity': 'medium',
                'description': 'Debug mode enabled'
            }
        }
        
        for scan_dir in self.security_config['scan_directories']:
            scan_path = Path(scan_dir)
            if not scan_path.exists():
                continue
            
            for py_file in scan_path.rglob('*.py'):
                if any(pattern in str(py_file) for pattern in self.security_config['excluded_patterns']):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        for check_name, check_config in network_patterns.items():
                            if re.search(check_config['pattern'], line, re.IGNORECASE):
                                vuln = SecurityVulnerability(
                                    vuln_id=f"network_{check_name}_{py_file.name}_{line_num}",
                                    severity=check_config['severity'],
                                    category='Network Security',
                                    title=f'Network Security Issue: {check_name}',
                                    description=check_config['description'],
                                    file_path=str(py_file),
                                    line_number=line_num,
                                    code_snippet=line.strip(),
                                    recommendation='Follow secure network communication practices',
                                    cwe_id='CWE-319',
                                    cvss_score=5.0 if check_config['severity'] == 'medium' else 2.0
                                )
                                vulnerabilities.append(vuln)
                                
                except Exception as e:
                    self.logger.warning(f"ネットワークセキュリティチェックエラー {py_file}: {e}")
        
        return vulnerabilities
    
    def _calculate_security_score(self, vulnerabilities: List[SecurityVulnerability]) -> float:
        """セキュリティスコア計算（100点満点）"""
        if not vulnerabilities:
            return 100.0
        
        total_penalty = sum(
            self.security_config['severity_weights'].get(vuln.severity, 1.0)
            for vuln in vulnerabilities
        )
        
        # ベーススコアから脆弱性の重要度に応じたペナルティを差し引き
        base_score = 100.0
        adjusted_score = max(0.0, base_score - total_penalty)
        
        return adjusted_score
    
    def _determine_risk_level(self, security_score: float) -> str:
        """リスクレベル判定"""
        thresholds = self.security_config['risk_thresholds']
        
        if security_score >= thresholds['low']:
            return 'low'
        elif security_score >= thresholds['medium']:
            return 'medium'
        elif security_score >= thresholds['high']:
            return 'high'
        else:
            return 'critical'
    
    def _get_recommendation(self, rule_name: str) -> str:
        """推奨対策取得"""
        recommendations = {
            'hardcoded_secrets': 'Use environment variables or secure configuration management',
            'sql_injection': 'Use parameterized queries or ORM with proper escaping',
            'command_injection': 'Validate and sanitize all user inputs before system calls',
            'path_traversal': 'Validate file paths and use safe path operations',
            'weak_crypto': 'Use strong cryptographic algorithms (SHA-256, AES-256)',
            'information_disclosure': 'Remove sensitive information from logs and error messages',
            'error_handling': 'Implement proper error handling with specific exception types'
        }
        
        return recommendations.get(rule_name, 'Follow security best practices')
    
    def _get_cvss_score(self, severity: str) -> float:
        """CVSS基本スコア取得"""
        cvss_mapping = {
            'critical': 9.0,
            'high': 7.5,
            'medium': 5.0,
            'low': 2.0,
            'info': 0.5
        }
        
        return cvss_mapping.get(severity, 5.0)
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """バージョン比較（簡易実装）"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 長さを合わせる
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))
            
            for i in range(max_len):
                if v1_parts[i] < v2_parts[i]:
                    return -1
                elif v1_parts[i] > v2_parts[i]:
                    return 1
            
            return 0
        except Exception:
            return 0  # 比較失敗時は同等とみなす
    
    def _get_vulnerability_categories(self, vulnerabilities: List[SecurityVulnerability]) -> Dict[str, int]:
        """脆弱性カテゴリ分布"""
        categories = {}
        for vuln in vulnerabilities:
            categories[vuln.category] = categories.get(vuln.category, 0) + 1
        return categories
    
    def _get_severity_distribution(self, vulnerabilities: List[SecurityVulnerability]) -> Dict[str, int]:
        """重要度分布"""
        severities = {}
        for vuln in vulnerabilities:
            severities[vuln.severity] = severities.get(vuln.severity, 0) + 1
        return severities
    
    def _save_scan_result(self, scan_result: SecurityScanResult) -> None:
        """スキャン結果データベース保存"""
        with sqlite3.connect(str(self.db_path)) as conn:
            # スキャン結果保存
            conn.execute("""
                INSERT INTO security_scans 
                (scan_id, scan_type, total_files_scanned, security_score, risk_level,
                 scan_duration, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_result.scan_id,
                scan_result.scan_type,
                scan_result.total_files_scanned,
                scan_result.security_score,
                scan_result.risk_level,
                scan_result.scan_duration,
                scan_result.timestamp.isoformat(),
                json.dumps(scan_result.metadata, ensure_ascii=False)
            ))
            
            # 脆弱性保存
            for vuln in scan_result.vulnerabilities:
                conn.execute("""
                    INSERT INTO vulnerabilities 
                    (scan_id, vuln_id, severity, category, title, description,
                     file_path, line_number, code_snippet, recommendation, cwe_id,
                     cvss_score, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    scan_result.scan_id,
                    vuln.vuln_id,
                    vuln.severity,
                    vuln.category,
                    vuln.title,
                    vuln.description,
                    vuln.file_path,
                    vuln.line_number,
                    vuln.code_snippet,
                    vuln.recommendation,
                    vuln.cwe_id,
                    vuln.cvss_score,
                    vuln.timestamp.isoformat()
                ))
            
            conn.commit()
    
    def get_scan_history(self, days: int = 30) -> List[SecurityScanResult]:
        """スキャン履歴取得"""
        since = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT scan_id, scan_type, total_files_scanned, security_score,
                       risk_level, scan_duration, timestamp, metadata
                FROM security_scans 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (since.isoformat(),))
            
            scans = []
            for row in cursor:
                # 脆弱性詳細取得
                vuln_cursor = conn.execute("""
                    SELECT vuln_id, severity, category, title, description,
                           file_path, line_number, code_snippet, recommendation,
                           cwe_id, cvss_score, timestamp
                    FROM vulnerabilities 
                    WHERE scan_id = ?
                """, (row[0],))
                
                vulnerabilities = []
                for vuln_row in vuln_cursor:
                    vuln = SecurityVulnerability(
                        vuln_id=vuln_row[0],
                        severity=vuln_row[1],
                        category=vuln_row[2],
                        title=vuln_row[3],
                        description=vuln_row[4],
                        file_path=vuln_row[5],
                        line_number=vuln_row[6],
                        code_snippet=vuln_row[7],
                        recommendation=vuln_row[8],
                        cwe_id=vuln_row[9],
                        cvss_score=vuln_row[10],
                        timestamp=datetime.fromisoformat(vuln_row[11])
                    )
                    vulnerabilities.append(vuln)
                
                scan = SecurityScanResult(
                    scan_id=row[0],
                    scan_type=row[1],
                    total_files_scanned=row[2],
                    vulnerabilities=vulnerabilities,
                    security_score=row[3],
                    risk_level=row[4],
                    scan_duration=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    metadata=json.loads(row[7]) if row[7] else {}
                )
                scans.append(scan)
            
            return scans
    
    def generate_security_report(self, days: int = 7) -> Dict[str, Any]:
        """セキュリティレポート生成"""
        recent_scans = self.get_scan_history(days)
        
        if not recent_scans:
            return {
                'status': 'no_data',
                'message': f'過去{days}日間のセキュリティスキャンデータがありません'
            }
        
        latest_scan = recent_scans[0]
        
        # トレンド分析
        scores = [scan.security_score for scan in recent_scans]
        score_trend = 'stable'
        if len(scores) > 1:
            if scores[0] > scores[-1] + 5:
                score_trend = 'improving'
            elif scores[0] < scores[-1] - 5:
                score_trend = 'degrading'
        
        # 重要脆弱性統計
        critical_vulns = [
            vuln for scan in recent_scans
            for vuln in scan.vulnerabilities
            if vuln.severity in ['critical', 'high']
        ]
        
        return {
            'status': 'success',
            'latest_scan': {
                'scan_id': latest_scan.scan_id,
                'security_score': latest_scan.security_score,
                'risk_level': latest_scan.risk_level,
                'vulnerabilities_count': len(latest_scan.vulnerabilities),
                'timestamp': latest_scan.timestamp.isoformat()
            },
            'trend_analysis': {
                'score_trend': score_trend,
                'average_score': sum(scores) / len(scores),
                'scan_frequency': len(recent_scans)
            },
            'vulnerability_summary': {
                'critical_high_count': len(critical_vulns),
                'category_distribution': latest_scan.metadata.get('vulnerability_categories', {}),
                'severity_distribution': latest_scan.metadata.get('severity_distribution', {})
            },
            'recommendations': self._generate_security_recommendations(latest_scan)
        }
    
    def _generate_security_recommendations(self, scan_result: SecurityScanResult) -> List[str]:
        """セキュリティ推奨事項生成"""
        recommendations = []
        
        if scan_result.security_score < 70:
            recommendations.append("セキュリティスコアが低下しています。緊急の対応が必要です。")
        
        # 重要度別推奨事項
        critical_vulns = [v for v in scan_result.vulnerabilities if v.severity == 'critical']
        high_vulns = [v for v in scan_result.vulnerabilities if v.severity == 'high']
        
        if critical_vulns:
            recommendations.append(f"{len(critical_vulns)}件の重要な脆弱性があります。直ちに修正してください。")
        
        if high_vulns:
            recommendations.append(f"{len(high_vulns)}件の高リスク脆弱性があります。優先的に対応してください。")
        
        # カテゴリ別推奨事項
        categories = scan_result.metadata.get('vulnerability_categories', {})
        
        if categories.get('Authentication', 0) > 0:
            recommendations.append("認証関連の脆弱性が検出されました。シークレット管理を見直してください。")
        
        if categories.get('Injection', 0) > 0:
            recommendations.append("インジェクション攻撃の脆弱性があります。入力検証を強化してください。")
        
        if not recommendations:
            recommendations.append("セキュリティ状態は良好です。定期的なスキャンを継続してください。")
        
        return recommendations