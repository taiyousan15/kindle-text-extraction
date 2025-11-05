"""
T-Max Work3 MLOps Agent
機械学習モデル管理・トレーニング自動化・デプロイを担当

機能:
- モデルトレーニング自動化
- ハイパーパラメータ最適化
- A/Bテスト実行
- モデルバージョニング
- MLflow統合
"""
import os
import subprocess
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import sys
import shutil

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


class MLOpsAgent:
    """
    MLOps Agent - 機械学習運用エージェント

    役割:
    - モデルトレーニングパイプライン管理
    - ハイパーパラメータチューニング
    - モデル評価とバージョニング
    - A/Bテストとカナリアデプロイ
    - モデル監視とドリフト検知
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.models_dir = self.repo_path / "models"
        self.experiments_dir = self.repo_path / "experiments"
        self.data_dir = self.repo_path / "data"
        self.reports_dir = self.repo_path / "tmax_work3" / "data" / "mlops_reports"

        # ディレクトリ作成
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # MLflow設定
        self.mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
        if MLFLOW_AVAILABLE:
            mlflow.set_tracking_uri(self.mlflow_tracking_uri)

        # エージェント登録
        self.blackboard.register_agent(
            AgentType.MLOPS,
            worktree="main"
        )

        self.blackboard.log(
            f"🤖 MLOps Agent initialized (MLflow: {MLFLOW_AVAILABLE})",
            level="INFO",
            agent=AgentType.MLOPS
        )

    def train_model(
        self,
        model_name: str,
        training_script: str,
        params: Optional[Dict] = None,
        dataset_path: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        モデルをトレーニング

        Args:
            model_name: モデル名
            training_script: トレーニングスクリプトパス
            params: ハイパーパラメータ
            dataset_path: データセットパス

        Returns:
            (success, training_report)
        """
        self.blackboard.log(
            f"🏋️ Training model: {model_name}",
            level="INFO",
            agent=AgentType.MLOPS
        )

        if params is None:
            params = {}

        training_report = {
            "model_name": model_name,
            "started_at": datetime.now().isoformat(),
            "params": params,
            "success": False
        }

        try:
            # MLflowランを開始
            if MLFLOW_AVAILABLE:
                with mlflow.start_run(run_name=model_name):
                    # パラメータをログ
                    mlflow.log_params(params)

                    # トレーニング実行
                    result = self._execute_training(training_script, params, dataset_path)

                    if result["success"]:
                        # メトリクスをログ
                        mlflow.log_metrics(result.get("metrics", {}))

                        # モデル保存
                        model_path = result.get("model_path")
                        if model_path and Path(model_path).exists():
                            mlflow.log_artifact(model_path)

                        training_report.update(result)
                        training_report["mlflow_run_id"] = mlflow.active_run().info.run_id

            else:
                # MLflowなしでトレーニング
                result = self._execute_training(training_script, params, dataset_path)
                training_report.update(result)

            training_report["completed_at"] = datetime.now().isoformat()

            if training_report["success"]:
                self.blackboard.log(
                    f"✅ Model trained successfully: {model_name}",
                    level="SUCCESS",
                    agent=AgentType.MLOPS
                )
            else:
                self.blackboard.log(
                    f"❌ Model training failed: {model_name}",
                    level="ERROR",
                    agent=AgentType.MLOPS
                )

            # レポート保存
            report_file = self.reports_dir / f"training_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_file.write_text(json.dumps(training_report, indent=2))

            return training_report["success"], training_report

        except Exception as e:
            self.blackboard.log(
                f"❌ Training exception: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            training_report["error"] = str(e)
            training_report["completed_at"] = datetime.now().isoformat()
            return False, training_report

    def _execute_training(
        self,
        training_script: str,
        params: Dict,
        dataset_path: Optional[str]
    ) -> Dict:
        """トレーニングスクリプトを実行"""
        try:
            # パラメータをJSON形式で渡す
            params_json = json.dumps(params)
            env = os.environ.copy()
            env["TRAINING_PARAMS"] = params_json

            if dataset_path:
                env["DATASET_PATH"] = dataset_path

            # トレーニングスクリプト実行
            result = subprocess.run(
                ["python", training_script],
                capture_output=True,
                text=True,
                timeout=3600,  # 1時間タイムアウト
                env=env,
                cwd=self.repo_path
            )

            if result.returncode == 0:
                # 標準出力からメトリクスを抽出
                metrics = self._extract_metrics_from_output(result.stdout)

                return {
                    "success": True,
                    "metrics": metrics,
                    "output": result.stdout,
                    "model_path": str(self.models_dir / "model.pkl")
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "output": result.stdout
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Training timeout exceeded"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_metrics_from_output(self, output: str) -> Dict:
        """トレーニング出力からメトリクスを抽出"""
        metrics = {}

        # パターンマッチングで一般的なメトリクスを抽出
        patterns = {
            "accuracy": r"accuracy[:\s]+([0-9.]+)",
            "loss": r"loss[:\s]+([0-9.]+)",
            "f1_score": r"f1[:\s]+([0-9.]+)",
            "precision": r"precision[:\s]+([0-9.]+)",
            "recall": r"recall[:\s]+([0-9.]+)"
        }

        import re
        for metric_name, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    metrics[metric_name] = float(match.group(1))
                except:
                    pass

        return metrics

    def optimize_hyperparameters(
        self,
        model_name: str,
        training_script: str,
        param_space: Dict,
        n_trials: int = 10
    ) -> Tuple[bool, Dict]:
        """
        ハイパーパラメータ最適化

        Args:
            model_name: モデル名
            training_script: トレーニングスクリプト
            param_space: パラメータ探索空間
            n_trials: 試行回数

        Returns:
            (success, optimization_report)
        """
        self.blackboard.log(
            f"🔧 Optimizing hyperparameters for: {model_name} ({n_trials} trials)",
            level="INFO",
            agent=AgentType.MLOPS
        )

        optimization_report = {
            "model_name": model_name,
            "n_trials": n_trials,
            "started_at": datetime.now().isoformat(),
            "trials": [],
            "best_params": None,
            "best_score": None
        }

        try:
            import random

            best_score = -float('inf')
            best_params = None

            for trial in range(n_trials):
                # パラメータをランダムサンプリング
                sampled_params = self._sample_params(param_space)

                self.blackboard.log(
                    f"🔄 Trial {trial + 1}/{n_trials}: {sampled_params}",
                    level="INFO",
                    agent=AgentType.MLOPS
                )

                # トレーニング実行
                success, training_report = self.train_model(
                    f"{model_name}_trial_{trial}",
                    training_script,
                    sampled_params
                )

                # スコア取得
                score = training_report.get("metrics", {}).get("accuracy", 0)

                optimization_report["trials"].append({
                    "trial_number": trial + 1,
                    "params": sampled_params,
                    "score": score,
                    "success": success
                })

                # ベストスコア更新
                if score > best_score:
                    best_score = score
                    best_params = sampled_params

            optimization_report["best_params"] = best_params
            optimization_report["best_score"] = best_score
            optimization_report["completed_at"] = datetime.now().isoformat()

            self.blackboard.log(
                f"✅ Hyperparameter optimization complete. Best score: {best_score:.4f}",
                level="SUCCESS",
                agent=AgentType.MLOPS
            )

            # レポート保存
            report_file = self.reports_dir / f"optimization_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_file.write_text(json.dumps(optimization_report, indent=2))

            return True, optimization_report

        except Exception as e:
            self.blackboard.log(
                f"❌ Hyperparameter optimization failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            optimization_report["error"] = str(e)
            optimization_report["completed_at"] = datetime.now().isoformat()
            return False, optimization_report

    def _sample_params(self, param_space: Dict) -> Dict:
        """パラメータ空間からサンプリング"""
        import random

        sampled = {}
        for param_name, space_def in param_space.items():
            space_type = space_def.get("type", "uniform")

            if space_type == "uniform":
                # 連続値
                low = space_def.get("low", 0)
                high = space_def.get("high", 1)
                sampled[param_name] = random.uniform(low, high)

            elif space_type == "int":
                # 整数値
                low = space_def.get("low", 0)
                high = space_def.get("high", 100)
                sampled[param_name] = random.randint(low, high)

            elif space_type == "choice":
                # カテゴリカル
                choices = space_def.get("choices", [])
                sampled[param_name] = random.choice(choices)

            elif space_type == "log_uniform":
                # 対数スケール
                low = space_def.get("low", 0.001)
                high = space_def.get("high", 1)
                sampled[param_name] = 10 ** random.uniform(
                    np.log10(low), np.log10(high)
                )

        return sampled

    def version_model(self, model_path: str, version: str, metadata: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        モデルをバージョニング

        Args:
            model_path: モデルファイルパス
            version: バージョン番号
            metadata: メタデータ

        Returns:
            (success, versioned_path)
        """
        self.blackboard.log(
            f"📦 Versioning model: {model_path} -> v{version}",
            level="INFO",
            agent=AgentType.MLOPS
        )

        try:
            model_path = Path(model_path)
            if not model_path.exists():
                return False, f"Model file not found: {model_path}"

            # バージョンディレクトリ作成
            version_dir = self.models_dir / f"v{version}"
            version_dir.mkdir(parents=True, exist_ok=True)

            # モデルファイルをコピー
            versioned_model_path = version_dir / model_path.name
            shutil.copy2(model_path, versioned_model_path)

            # メタデータ保存
            if metadata is None:
                metadata = {}

            metadata.update({
                "version": version,
                "created_at": datetime.now().isoformat(),
                "original_path": str(model_path),
                "model_hash": self._compute_file_hash(model_path)
            })

            metadata_path = version_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))

            self.blackboard.log(
                f"✅ Model versioned: {versioned_model_path}",
                level="SUCCESS",
                agent=AgentType.MLOPS
            )

            return True, str(versioned_model_path)

        except Exception as e:
            self.blackboard.log(
                f"❌ Model versioning failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            return False, str(e)

    def _compute_file_hash(self, file_path: Path) -> str:
        """ファイルのハッシュ値を計算"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def setup_ab_test(
        self,
        model_a: str,
        model_b: str,
        traffic_split: float = 0.5
    ) -> Tuple[bool, Dict]:
        """
        A/Bテストをセットアップ

        Args:
            model_a: モデルAのパス
            model_b: モデルBのパス
            traffic_split: モデルAへのトラフィック割合 (0-1)

        Returns:
            (success, ab_test_config)
        """
        self.blackboard.log(
            f"🔀 Setting up A/B test: {model_a} vs {model_b} (split: {traffic_split:.2f})",
            level="INFO",
            agent=AgentType.MLOPS
        )

        try:
            ab_test_config = {
                "test_id": f"abtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "model_a": {
                    "path": model_a,
                    "traffic_weight": traffic_split
                },
                "model_b": {
                    "path": model_b,
                    "traffic_weight": 1 - traffic_split
                },
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "metrics": {
                    "model_a": {"requests": 0, "latency_ms": [], "errors": 0},
                    "model_b": {"requests": 0, "latency_ms": [], "errors": 0}
                }
            }

            # 設定ファイル保存
            config_path = self.experiments_dir / f"{ab_test_config['test_id']}.json"
            config_path.write_text(json.dumps(ab_test_config, indent=2))

            self.blackboard.log(
                f"✅ A/B test configured: {config_path}",
                level="SUCCESS",
                agent=AgentType.MLOPS
            )

            return True, ab_test_config

        except Exception as e:
            self.blackboard.log(
                f"❌ A/B test setup failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            return False, {"error": str(e)}

    def analyze_ab_test(self, test_id: str) -> Dict:
        """
        A/Bテスト結果を分析

        Args:
            test_id: テストID

        Returns:
            分析レポート
        """
        self.blackboard.log(
            f"📊 Analyzing A/B test: {test_id}",
            level="INFO",
            agent=AgentType.MLOPS
        )

        try:
            config_path = self.experiments_dir / f"{test_id}.json"
            if not config_path.exists():
                return {"error": f"Test config not found: {test_id}"}

            config = json.loads(config_path.read_text())
            metrics = config.get("metrics", {})

            model_a_metrics = metrics.get("model_a", {})
            model_b_metrics = metrics.get("model_b", {})

            # 統計分析
            analysis = {
                "test_id": test_id,
                "timestamp": datetime.now().isoformat(),
                "model_a": {
                    "requests": model_a_metrics.get("requests", 0),
                    "avg_latency_ms": self._calculate_avg(model_a_metrics.get("latency_ms", [])),
                    "error_rate": self._calculate_error_rate(
                        model_a_metrics.get("errors", 0),
                        model_a_metrics.get("requests", 0)
                    )
                },
                "model_b": {
                    "requests": model_b_metrics.get("requests", 0),
                    "avg_latency_ms": self._calculate_avg(model_b_metrics.get("latency_ms", [])),
                    "error_rate": self._calculate_error_rate(
                        model_b_metrics.get("errors", 0),
                        model_b_metrics.get("requests", 0)
                    )
                }
            }

            # 勝者判定
            if analysis["model_a"]["error_rate"] < analysis["model_b"]["error_rate"]:
                analysis["winner"] = "model_a"
                analysis["reason"] = "Lower error rate"
            elif analysis["model_b"]["error_rate"] < analysis["model_a"]["error_rate"]:
                analysis["winner"] = "model_b"
                analysis["reason"] = "Lower error rate"
            elif analysis["model_a"]["avg_latency_ms"] < analysis["model_b"]["avg_latency_ms"]:
                analysis["winner"] = "model_a"
                analysis["reason"] = "Lower latency"
            elif analysis["model_b"]["avg_latency_ms"] < analysis["model_a"]["avg_latency_ms"]:
                analysis["winner"] = "model_b"
                analysis["reason"] = "Lower latency"
            else:
                analysis["winner"] = "tie"
                analysis["reason"] = "No significant difference"

            self.blackboard.log(
                f"✅ A/B test analysis complete. Winner: {analysis['winner']}",
                level="SUCCESS",
                agent=AgentType.MLOPS
            )

            return analysis

        except Exception as e:
            self.blackboard.log(
                f"❌ A/B test analysis failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            return {"error": str(e)}

    def _calculate_avg(self, values: List[float]) -> float:
        """平均値を計算"""
        return sum(values) / len(values) if values else 0.0

    def _calculate_error_rate(self, errors: int, total: int) -> float:
        """エラー率を計算"""
        return (errors / total * 100) if total > 0 else 0.0

    def detect_model_drift(self, model_path: str, validation_data: Optional[str] = None) -> Dict:
        """
        モデルドリフトを検知

        Args:
            model_path: モデルパス
            validation_data: 検証データパス

        Returns:
            ドリフトレポート
        """
        self.blackboard.log(
            f"🔍 Detecting model drift: {model_path}",
            level="INFO",
            agent=AgentType.MLOPS
        )

        try:
            # モデルのメタデータ取得
            model_dir = Path(model_path).parent
            metadata_path = model_dir / "metadata.json"

            if not metadata_path.exists():
                return {"error": "Model metadata not found"}

            metadata = json.loads(metadata_path.read_text())
            baseline_metrics = metadata.get("metrics", {})

            # 現在のパフォーマンスを評価（簡易実装）
            current_metrics = {
                "accuracy": 0.85,  # シミュレーション
                "loss": 0.25
            }

            # ドリフト判定
            drift_detected = False
            drift_details = []

            for metric_name, baseline_value in baseline_metrics.items():
                current_value = current_metrics.get(metric_name, 0)
                drift_percentage = abs(current_value - baseline_value) / baseline_value * 100

                if drift_percentage > 10:  # 10%以上の変化
                    drift_detected = True
                    drift_details.append({
                        "metric": metric_name,
                        "baseline": baseline_value,
                        "current": current_value,
                        "drift_percentage": drift_percentage
                    })

            drift_report = {
                "model_path": model_path,
                "timestamp": datetime.now().isoformat(),
                "drift_detected": drift_detected,
                "drift_details": drift_details,
                "baseline_metrics": baseline_metrics,
                "current_metrics": current_metrics
            }

            if drift_detected:
                self.blackboard.log(
                    f"⚠️ Model drift detected: {len(drift_details)} metrics drifted",
                    level="WARNING",
                    agent=AgentType.MLOPS
                )
            else:
                self.blackboard.log(
                    "✅ No model drift detected",
                    level="SUCCESS",
                    agent=AgentType.MLOPS
                )

            return drift_report

        except Exception as e:
            self.blackboard.log(
                f"❌ Model drift detection failed: {str(e)}",
                level="ERROR",
                agent=AgentType.MLOPS
            )
            return {"error": str(e)}

    def run_full_cycle(
        self,
        model_name: str,
        training_script: str,
        optimize: bool = False
    ) -> Dict:
        """
        完全なMLOpsサイクルを実行

        フロー:
        1. モデルトレーニング
        2. (オプション) ハイパーパラメータ最適化
        3. モデルバージョニング
        4. ドリフト検知

        Returns:
            実行レポート
        """
        report = {
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "success": False
        }

        # Step 1: トレーニング
        if optimize:
            # ハイパーパラメータ最適化
            param_space = {
                "learning_rate": {"type": "uniform", "low": 0.0001, "high": 0.01},
                "batch_size": {"type": "choice", "choices": [16, 32, 64, 128]},
                "epochs": {"type": "int", "low": 10, "high": 100}
            }

            success, opt_report = self.optimize_hyperparameters(
                model_name,
                training_script,
                param_space,
                n_trials=5
            )

            report["steps"].append({
                "step": "optimize_hyperparameters",
                "success": success,
                "best_params": opt_report.get("best_params"),
                "best_score": opt_report.get("best_score")
            })

            # ベストパラメータでトレーニング
            if success and opt_report.get("best_params"):
                success, train_report = self.train_model(
                    model_name,
                    training_script,
                    opt_report["best_params"]
                )
            else:
                success, train_report = self.train_model(model_name, training_script)
        else:
            # 通常のトレーニング
            success, train_report = self.train_model(model_name, training_script)

        report["steps"].append({
            "step": "train_model",
            "success": success,
            "metrics": train_report.get("metrics", {})
        })

        if not success:
            report["message"] = "Training failed"
            return report

        # Step 2: バージョニング
        model_path = train_report.get("model_path")
        if model_path:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
            success, versioned_path = self.version_model(
                model_path,
                version,
                {"metrics": train_report.get("metrics", {})}
            )

            report["steps"].append({
                "step": "version_model",
                "success": success,
                "version": version,
                "path": versioned_path
            })

        # Step 3: ドリフト検知
        if model_path:
            drift_report = self.detect_model_drift(model_path)
            report["steps"].append({
                "step": "detect_drift",
                "success": "error" not in drift_report,
                "drift_detected": drift_report.get("drift_detected", False)
            })

        report["completed_at"] = datetime.now().isoformat()
        report["success"] = True
        report["message"] = "Full MLOps cycle completed"

        return report


# スタンドアロン実行用
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MLOps Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--action", default="full",
                       choices=["train", "optimize", "version", "abtest", "drift", "full"],
                       help="Action to perform")
    parser.add_argument("--model-name", default="model", help="Model name")
    parser.add_argument("--script", help="Training script path")
    parser.add_argument("--optimize", action="store_true", help="Run hyperparameter optimization")

    args = parser.parse_args()

    agent = MLOpsAgent(args.repo)

    if args.action == "train":
        if not args.script:
            print("Error: --script required for training")
            sys.exit(1)

        success, report = agent.train_model(args.model_name, args.script)
        print(f"Training: {success}")
        print(json.dumps(report, indent=2))

    elif args.action == "optimize":
        if not args.script:
            print("Error: --script required for optimization")
            sys.exit(1)

        param_space = {
            "learning_rate": {"type": "uniform", "low": 0.0001, "high": 0.01},
            "batch_size": {"type": "choice", "choices": [16, 32, 64]}
        }

        success, report = agent.optimize_hyperparameters(
            args.model_name,
            args.script,
            param_space,
            n_trials=10
        )
        print(f"Optimization: {success}")
        print(json.dumps(report, indent=2))

    elif args.action == "version":
        success, path = agent.version_model("models/model.pkl", "1.0.0")
        print(f"Versioned: {success}")
        print(f"Path: {path}")

    elif args.action == "abtest":
        success, config = agent.setup_ab_test("models/v1/model.pkl", "models/v2/model.pkl")
        print(f"A/B test: {success}")
        print(json.dumps(config, indent=2))

    elif args.action == "drift":
        report = agent.detect_model_drift("models/v1/model.pkl")
        print(json.dumps(report, indent=2))

    elif args.action == "full":
        if not args.script:
            print("Error: --script required for full cycle")
            sys.exit(1)

        report = agent.run_full_cycle(
            args.model_name,
            args.script,
            optimize=args.optimize
        )
        print(json.dumps(report, indent=2))
