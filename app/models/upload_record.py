"""
文件上传记录模型
"""
from datetime import datetime
import pytz
from app import db

class UploadRecord(db.Model):
    """文件上传记录"""
    __tablename__ = 'upload_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # 原始文件名
    stored_filename = db.Column(db.String(255), nullable=False)  # 存储的文件名
    file_path = db.Column(db.String(255), nullable=False)  # 存储路径
    file_size = db.Column(db.Integer, nullable=False)  # 文件大小(字节)
    upload_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(pytz.timezone('Asia/Shanghai')))  # 上传时间
    status = db.Column(db.String(20), default='pending')  # 状态: pending, completed, failed
    error_message = db.Column(db.String(255))  # 错误信息

    def __repr__(self):
        return f'<UploadRecord {self.filename}>'

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'stored_filename': self.stored_filename,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'upload_time': self.upload_time.isoformat(),
            'status': self.status,
            'error_message': self.error_message
        }