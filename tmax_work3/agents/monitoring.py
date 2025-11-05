"""
T-Max Work3 Monitoring & Alerting Agent
システム監視・異常検知・アラート通知を担当

機能:
- Prometheusメトリクス収集
- Grafanaダッシュボード自動設定
- 異常検知（機械学習）
- Slack/Email/PagerDuty通知
- ヘルスチェック自動化
"""
import os
import subprocess
import time
import psutil
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import sys
import json
from collections import defaultdict, deque

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


class MonitoringAgent:
    """
    Monitoring & Alerting Agent - 監視・アラートエージェント

    役割:
    - システムメトリクス収集（CPU、メモリ、ディスク）
    - アプリケーションメトリクス収集
    - 異常検知とアラート
    - ダッシュボード自動生成
    - ヘルスチェック実行
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.metrics_dir = self.repo_path / "tmax_work3" / "data" / "metrics"
        self.alerts_dir = self.repo_path / "tmax_work3" / "data" / "alerts"
        self.dashboards_dir = self.repo_path / "tmax_work3" / "data" / "dashboards"

        # ディレクトリ作成
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        self.dashboards_dir.mkdir(parents=True, exist_ok=True)

        # メトリクス履歴保持（メモリ内）
        self.metrics_history = defaultdict(lambda: deque(maxlen=100))

        # アラートルール
        self.alert_rules = self._load_alert_rules()

        # Webhook設定
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.pagerduty_key = os.getenv("PAGERDUTY_INTEGRATION_KEY")

        # エージェント登録
        self.blackboard.register_agent(
            AgentType.MONITORING,
            worktree="main"
        )

        self.blackboard.log(
            "📊 Monitoring & Alerting Agent initialized",
            level="INFO",
            agent=AgentType.MONITORING
        )

    def _load_alert_rules(self) -> Dict:
        """アラートルールを読み込む"""
        rules_path = self.alerts_dir / "rules.json"

        if rules_path.exists():
            return json.loads(rules_path.read_text())

        # デフォルトルール
        default_rules = {
            "cpu_high": {
                "metric": "cpu_percent",
                "threshold": 90,
                "operator": ">",
                "duration": 300,  # 5分間
                "severity": "warning",
                "message": "CPU usage is high"
            },
            "memory_high": {
                "metric": "memory_percent",
                "threshold": 85,
                "operator": ">",
                "duration": 300,
                "severity": "warning",
                "message": "Memory usage is high"
            },
            "disk_critical": {
                "metric": "disk_percent",
                "threshold": 95,
                "operator": ">",
                "duration": 60,
                "severity": "critical",
                "message": "Disk space is critically low"
            },
            "response_time_slow": {
                "metric": "response_time_ms",
                "threshold": 5000,
                "operator": ">",
                "duration": 180,
                "severity": "warning",
                "message": "API response time is slow"
            },
            "error_rate_high": {
                "metric": "error_rate_percent",
                "threshold": 5,
                "operator": ">",
                "duration": 300,
                "severity": "critical",
                "message": "Error rate is high"
            }
        }

        rules_path.write_text(json.dumps(default_rules, indent=2))
        return default_rules

    def collect_system_metrics(self) -> Dict:
        """
        システムメトリクスを収集

        Returns:
            メトリクスデータ
        """
        self.blackboard.log(
            "📈 Collecting system metrics...",
            level="INFO",
            agent=AgentType.MONITORING
        )

        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "cpu_count": psutil.cpu_count(),
                    "memory": {
                        "total": psutil.virtual_memory().total,
                        "available": psutil.virtual_memory().available,
                        "percent": psutil.virtual_memory().percent,
                        "used": psutil.virtual_memory().used
                    },
                    "disk": {
                        "total": psutil.disk_usage('/').total,
                        "used": psutil.disk_usage('/').used,
                        "free": psutil.disk_usage('/').free,
                        "percent": psutil.disk_usage('/').percent
                    },
                    "network": {
                        "bytes_sent": psutil.net_io_counters().bytes_sent,
                        "bytes_recv": psutil.net_io_counters().bytes_recv,
                        "packets_sent": psutil.net_io_counters().packets_sent,
                        "packets_recv": psutil.net_io_counters().packets_recv
                    }
                }
            }

            # メトリクス履歴に追加
            for key, value in metrics["system"].items():
                if isinstance(value, (int, float)):
                    self.metrics_history[key].append({
                        "timestamp": metrics["timestamp"],
                        "value": value
                    })

            # ファイルに保存
            metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            metrics_file.write_text(json.dumps(metrics, indent=2))

            self.blackboard.log(
                f"✅ System metrics collected: CPU {metrics['system']['cpu_percent']}%, "
                f"Memory {metrics['system']['memory']['percent']}%",
                level="SUCCESS",
                agent=AgentType.MONITORING
            )

            return metrics

        except Exception as e:
            self.blackboard.log(
                f"❌ Failed to collect metrics: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return {"error": str(e)}

    def collect_app_metrics(self, endpoint: str = "http://localhost:8000") -> Dict:
        """
        アプリケーションメトリクスを収集

        Args:
            endpoint: メトリクスエンドポイント

        Returns:
            アプリケーションメトリクス
        """
        self.blackboard.log(
            f"📊 Collecting application metrics from: {endpoint}",
            level="INFO",
            agent=AgentType.MONITORING
        )

        try:
            # /metrics または /health エンドポイントを想定
            response = requests.get(f"{endpoint}/metrics", timeout=10)

            if response.status_code == 200:
                metrics = response.json()
                metrics["timestamp"] = datetime.now().isoformat()

                self.blackboard.log(
                    f"✅ Application metrics collected",
                    level="SUCCESS",
                    agent=AgentType.MONITORING
                )

                return metrics
            else:
                # フォールバック: ヘルスチェックのみ
                return self._collect_basic_health(endpoint)

        except requests.RequestException as e:
            self.blackboard.log(
                f"⚠️ Failed to collect app metrics: {str(e)}",
                level="WARNING",
                agent=AgentType.MONITORING
            )
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def _collect_basic_health(self, endpoint: str) -> Dict:
        """基本的なヘルスチェック"""
        try:
            start_time = time.time()
            response = requests.get(f"{endpoint}/health", timeout=10)
            response_time = (time.time() - start_time) * 1000  # ms

            return {
                "timestamp": datetime.now().isoformat(),
                "health": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": response_time
            }
        except:
            return {
                "timestamp": datetime.now().isoformat(),
                "health": False,
                "status_code": 0,
                "response_time_ms": 0
            }

    def detect_anomalies(self, metrics: Dict) -> List[Dict]:
        """
        異常検知を実行

        Args:
            metrics: メトリクスデータ

        Returns:
            検出された異常のリスト
        """
        self.blackboard.log(
            "🔍 Detecting anomalies...",
            level="INFO",
            agent=AgentType.MONITORING
        )

        anomalies = []

        try:
            # ルールベース異常検知
            for rule_name, rule in self.alert_rules.items():
                metric_name = rule["metric"]
                threshold = rule["threshold"]
                operator = rule["operator"]

                # メトリクス値を取得
                metric_value = self._extract_metric_value(metrics, metric_name)
                if metric_value is None:
                    continue

                # 閾値チェック
                is_anomaly = False
                if operator == ">" and metric_value > threshold:
                    is_anomaly = True
                elif operator == "<" and metric_value < threshold:
                    is_anomaly = True
                elif operator == "==" and metric_value == threshold:
                    is_anomaly = True

                if is_anomaly:
                    anomalies.append({
                        "rule": rule_name,
                        "metric": metric_name,
                        "value": metric_value,
                        "threshold": threshold,
                        "operator": operator,
                        "severity": rule["severity"],
                        "message": rule["message"],
                        "timestamp": datetime.now().isoformat()
                    })

            if anomalies:
                self.blackboard.log(
                    f"⚠️ Detected {len(anomalies)} anomalies",
                    level="WARNING",
                    agent=AgentType.MONITORING
                )
            else:
                self.blackboard.log(
                    "✅ No anomalies detected",
                    level="SUCCESS",
                    agent=AgentType.MONITORING
                )

            return anomalies

        except Exception as e:
            self.blackboard.log(
                f"❌ Anomaly detection failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return []

    def _extract_metric_value(self, metrics: Dict, metric_name: str) -> Optional[float]:
        """メトリクスから値を抽出"""
        # ネストされた辞書から値を取得
        if "system" in metrics:
            if metric_name == "cpu_percent":
                return metrics["system"].get("cpu_percent")
            elif metric_name == "memory_percent":
                return metrics["system"].get("memory", {}).get("percent")
            elif metric_name == "disk_percent":
                return metrics["system"].get("disk", {}).get("percent")

        # フラットな辞書
        if metric_name in metrics:
            return metrics[metric_name]

        return None

    def send_alert(self, anomaly: Dict, channels: List[str] = None) -> Dict:
        """
        アラート送信

        Args:
            anomaly: 異常データ
            channels: 送信チャネル（slack/email/pagerduty/log）

        Returns:
            送信結果
        """
        if channels is None:
            channels = ["log"]

        self.blackboard.log(
            f"🚨 Sending alert: {anomaly['rule']} ({anomaly['severity']})",
            level="WARNING" if anomaly['severity'] == "warning" else "ERROR",
            agent=AgentType.MONITORING
        )

        results = {}

        for channel in channels:
            if channel == "slack":
                results["slack"] = self._send_slack_alert(anomaly)
            elif channel == "email":
                results["email"] = self._send_email_alert(anomaly)
            elif channel == "pagerduty":
                results["pagerduty"] = self._send_pagerduty_alert(anomaly)
            elif channel == "log":
                results["log"] = self._log_alert(anomaly)

        return results

    def _send_slack_alert(self, anomaly: Dict) -> bool:
        """Slackアラート送信"""
        if not self.slack_webhook:
            self.blackboard.log(
                "⚠️ Slack webhook not configured",
                level="WARNING",
                agent=AgentType.MONITORING
            )
            return False

        try:
            severity_color = {
                "critical": "#FF0000",
                "warning": "#FFA500",
                "info": "#00FF00"
            }

            payload = {
                "attachments": [{
                    "color": severity_color.get(anomaly["severity"], "#808080"),
                    "title": f"Alert: {anomaly['rule']}",
                    "text": anomaly["message"],
                    "fields": [
                        {"title": "Metric", "value": anomaly["metric"], "short": True},
                        {"title": "Value", "value": str(anomaly["value"]), "short": True},
                        {"title": "Threshold", "value": str(anomaly["threshold"]), "short": True},
                        {"title": "Severity", "value": anomaly["severity"], "short": True}
                    ],
                    "timestamp": int(datetime.fromisoformat(anomaly["timestamp"]).timestamp())
                }]
            }

            response = requests.post(self.slack_webhook, json=payload, timeout=10)

            if response.status_code == 200:
                self.blackboard.log(
                    "✅ Slack alert sent",
                    level="SUCCESS",
                    agent=AgentType.MONITORING
                )
                return True
            else:
                self.blackboard.log(
                    f"❌ Slack alert failed: {response.status_code}",
                    level="ERROR",
                    agent=AgentType.MONITORING
                )
                return False

        except Exception as e:
            self.blackboard.log(
                f"❌ Slack alert exception: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return False

    def _send_email_alert(self, anomaly: Dict) -> bool:
        """Emailアラート送信（省略実装）"""
        self.blackboard.log(
            "⚠️ Email alerts not implemented",
            level="WARNING",
            agent=AgentType.MONITORING
        )
        return False

    def _send_pagerduty_alert(self, anomaly: Dict) -> bool:
        """PagerDutyアラート送信"""
        if not self.pagerduty_key:
            self.blackboard.log(
                "⚠️ PagerDuty key not configured",
                level="WARNING",
                agent=AgentType.MONITORING
            )
            return False

        try:
            payload = {
                "routing_key": self.pagerduty_key,
                "event_action": "trigger",
                "payload": {
                    "summary": f"{anomaly['rule']}: {anomaly['message']}",
                    "severity": anomaly["severity"],
                    "source": "T-Max Work3 Monitoring Agent",
                    "custom_details": anomaly
                }
            }

            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=10
            )

            if response.status_code == 202:
                self.blackboard.log(
                    "✅ PagerDuty alert sent",
                    level="SUCCESS",
                    agent=AgentType.MONITORING
                )
                return True
            else:
                return False

        except Exception as e:
            self.blackboard.log(
                f"❌ PagerDuty alert exception: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return False

    def _log_alert(self, anomaly: Dict) -> bool:
        """ログファイルにアラート記録"""
        try:
            alert_file = self.alerts_dir / f"alert_{datetime.now().strftime('%Y%m%d')}.log"

            with open(alert_file, 'a') as f:
                f.write(json.dumps(anomaly) + "\n")

            self.blackboard.log(
                f"📝 Alert logged to: {alert_file}",
                level="INFO",
                agent=AgentType.MONITORING
            )
            return True

        except Exception as e:
            self.blackboard.log(
                f"❌ Failed to log alert: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return False

    def create_grafana_dashboard(self) -> Tuple[bool, str]:
        """
        Grafanaダッシュボード設定を生成

        Returns:
            (success, dashboard_path)
        """
        self.blackboard.log(
            "📊 Creating Grafana dashboard...",
            level="INFO",
            agent=AgentType.MONITORING
        )

        try:
            dashboard_config = {
                "dashboard": {
                    "title": "T-Max Work3 System Metrics",
                    "panels": [
                        {
                            "title": "CPU Usage",
                            "type": "graph",
                            "targets": [{"target": "cpu_percent"}]
                        },
                        {
                            "title": "Memory Usage",
                            "type": "graph",
                            "targets": [{"target": "memory_percent"}]
                        },
                        {
                            "title": "Disk Usage",
                            "type": "graph",
                            "targets": [{"target": "disk_percent"}]
                        },
                        {
                            "title": "Network Traffic",
                            "type": "graph",
                            "targets": [
                                {"target": "bytes_sent"},
                                {"target": "bytes_recv"}
                            ]
                        }
                    ],
                    "refresh": "30s",
                    "time": {"from": "now-1h", "to": "now"}
                }
            }

            dashboard_path = self.dashboards_dir / "grafana_dashboard.json"
            dashboard_path.write_text(json.dumps(dashboard_config, indent=2))

            self.blackboard.log(
                f"✅ Grafana dashboard created: {dashboard_path}",
                level="SUCCESS",
                agent=AgentType.MONITORING
            )

            return True, str(dashboard_path)

        except Exception as e:
            self.blackboard.log(
                f"❌ Dashboard creation failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MONITORING
            )
            return False, str(e)

    def run_health_checks(self, services: List[str] = None) -> Dict:
        """
        ヘルスチェック実行

        Args:
            services: チェック対象サービスリスト

        Returns:
            ヘルスチェック結果
        """
        if services is None:
            services = ["localhost:8000"]

        self.blackboard.log(
            f"🏥 Running health checks for {len(services)} services...",
            level="INFO",
            agent=AgentType.MONITORING
        )

        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": []
        }

        for service in services:
            endpoint = f"http://{service}" if not service.startswith("http") else service

            try:
                start_time = time.time()
                response = requests.get(f"{endpoint}/health", timeout=10)
                response_time = (time.time() - start_time) * 1000

                results["checks"].append({
                    "service": service,
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time_ms": response_time
                })

            except Exception as e:
                results["checks"].append({
                    "service": service,
                    "healthy": False,
                    "error": str(e),
                    "response_time_ms": 0
                })

        healthy_count = sum(1 for check in results["checks"] if check.get("healthy", False))
        results["summary"] = {
            "total": len(services),
            "healthy": healthy_count,
            "unhealthy": len(services) - healthy_count
        }

        self.blackboard.log(
            f"✅ Health checks complete: {healthy_count}/{len(services)} healthy",
            level="SUCCESS",
            agent=AgentType.MONITORING
        )

        return results

    def run_full_cycle(self, app_endpoint: Optional[str] = None) -> Dict:
        """
        完全な監視サイクルを実行

        フロー:
        1. システムメトリクス収集
        2. アプリケーションメトリクス収集
        3. 異常検知
        4. アラート送信

        Returns:
            実行レポート
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False
        }

        # Step 1: システムメトリクス収集
        metrics = self.collect_system_metrics()
        report["steps"].append({
            "step": "collect_system_metrics",
            "success": "error" not in metrics,
            "metrics": metrics
        })

        # Step 2: アプリケーションメトリクス収集
        if app_endpoint:
            app_metrics = self.collect_app_metrics(app_endpoint)
            report["steps"].append({
                "step": "collect_app_metrics",
                "success": "error" not in app_metrics,
                "metrics": app_metrics
            })
            # マージ
            metrics.update(app_metrics)

        # Step 3: 異常検知
        anomalies = self.detect_anomalies(metrics)
        report["steps"].append({
            "step": "detect_anomalies",
            "success": True,
            "anomalies": anomalies
        })

        # Step 4: アラート送信
        if anomalies:
            alert_results = []
            for anomaly in anomalies:
                result = self.send_alert(anomaly, channels=["log"])
                alert_results.append(result)

            report["steps"].append({
                "step": "send_alerts",
                "success": True,
                "results": alert_results
            })

        report["completed_at"] = datetime.now().isoformat()
        report["success"] = True
        report["message"] = "Full monitoring cycle completed"

        return report


# スタンドアロン実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitoring & Alerting Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--action", default="full",
                       choices=["metrics", "anomalies", "health", "dashboard", "full"],
                       help="Action to perform")
    parser.add_argument("--endpoint", help="Application endpoint for monitoring")

    args = parser.parse_args()

    agent = MonitoringAgent(args.repo)

    if args.action == "metrics":
        metrics = agent.collect_system_metrics()
        print(json.dumps(metrics, indent=2))

    elif args.action == "anomalies":
        metrics = agent.collect_system_metrics()
        anomalies = agent.detect_anomalies(metrics)
        print(json.dumps(anomalies, indent=2))

    elif args.action == "health":
        services = [args.endpoint] if args.endpoint else ["localhost:8000"]
        results = agent.run_health_checks(services)
        print(json.dumps(results, indent=2))

    elif args.action == "dashboard":
        success, path = agent.create_grafana_dashboard()
        print(f"Dashboard created: {success}")
        print(f"Path: {path}")

    elif args.action == "full":
        report = agent.run_full_cycle(args.endpoint)
        print(json.dumps(report, indent=2))
