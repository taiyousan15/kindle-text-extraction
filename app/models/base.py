"""
SQLAlchemy Base and Mixins

基本設定と共通Mixin
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, func
from datetime import datetime
from typing import Dict, Any
import uuid

Base = declarative_base()


class TimestampMixin:
    """タイムスタンプMixin（created_at, updated_at）"""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class UUIDMixin:
    """UUID主キーMixin"""
    @staticmethod
    def generate_uuid():
        return str(uuid.uuid4())


class SerializeMixin:
    """シリアライズMixin"""

    def to_dict(self, exclude: list = None) -> Dict[str, Any]:
        """
        モデルを辞書に変換

        Args:
            exclude: 除外するカラム名のリスト

        Returns:
            辞書形式のデータ
        """
        exclude = exclude or []
        data = {}

        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)

                # UUIDとdatetimeを文字列に変換
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, bytes):
                    # BYTEAは除外（大きすぎる）
                    continue

                data[column.name] = value

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        辞書からモデルインスタンスを作成

        Args:
            data: 辞書データ

        Returns:
            モデルインスタンス
        """
        # カラム名のみ抽出
        valid_keys = {c.name for c in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}

        return cls(**filtered_data)
