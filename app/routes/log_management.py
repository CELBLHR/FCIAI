"""
日志管理路由
提供日志查看和管理的API接口
"""
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from app.utils.logger import log_manager

# 创建Blueprint
router = Blueprint('log_management', __name__)

@router.route('/api/logs/list', methods=['GET'])
@login_required
def list_loggers():
    """获取所有日志记录器列表"""
    if not current_user.is_administrator():
        abort(403, "权限不足")

    try:
        loggers = log_manager.get_loggers()
        return jsonify(loggers)
    except Exception as e:
        abort(500, f"获取日志记录器列表失败: {str(e)}")

@router.route('/api/logs/query', methods=['POST'])
@login_required
def query_logs():
    """查询日志内容"""
    if not current_user.is_administrator():
        abort(403, "权限不足")

    data = request.get_json()
    if not data or 'logger_name' not in data:
        abort(400, "请提供有效的查询参数")

    try:
        # 解析请求参数
        logger_name = data.get('logger_name')
        start_time = None
        end_time = None

        # 改进的时间解析逻辑
        if data.get('start_time') and data.get('start_time').strip():
            start_time_str = data.get('start_time').strip()
            try:
                # 尝试多种时间格式
                if 'T' in start_time_str:
                    # ISO格式: 2025-06-01T23:14:33 或 2025-06-01T23:14:33Z
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                else:
                    # 标准格式: 2025-06-01 23:14:33
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # 尝试只有日期的格式: 2025-06-01
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d')
                except ValueError:
                    # 如果都失败，记录错误但不中断
                    print(f"无法解析开始时间: {start_time_str}")

        if data.get('end_time') and data.get('end_time').strip():
            end_time_str = data.get('end_time').strip()
            try:
                # 尝试多种时间格式
                if 'T' in end_time_str:
                    # ISO格式: 2025-06-01T23:14:33 或 2025-06-01T23:14:33Z
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                else:
                    # 标准格式: 2025-06-01 23:14:33
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # 尝试只有日期的格式: 2025-06-01，设置为当天结束
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%d')
                    end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
                except ValueError:
                    # 如果都失败，记录错误但不中断
                    print(f"无法解析结束时间: {end_time_str}")

        level = data.get('level')
        limit = int(data.get('limit', 100))

        # 添加调试信息
        print(f"日志查询参数:")
        print(f"  logger_name: {logger_name}")
        print(f"  start_time: {start_time}")
        print(f"  end_time: {end_time}")
        print(f"  level: {level}")
        print(f"  limit: {limit}")

        logs = log_manager.get_logs(
            name=logger_name,
            start_time=start_time,
            end_time=end_time,
            level=level,
            limit=limit
        )

        print(f"查询结果: {len(logs)} 条日志")
        if logs:
            print(f"第一条日志时间: {logs[0].get('timestamp_str', 'N/A')}")
            print(f"最后一条日志时间: {logs[-1].get('timestamp_str', 'N/A')}")

        return jsonify({
            "logs": logs,
            "debug_info": {
                "query_params": {
                    "logger_name": logger_name,
                    "start_time": start_time.isoformat() if start_time else None,
                    "end_time": end_time.isoformat() if end_time else None,
                    "level": level,
                    "limit": limit
                },
                "result_count": len(logs)
            }
        })
    except Exception as e:
        abort(500, str(e))

@router.route('/api/logs/level', methods=['POST'])
@login_required
def update_log_level():
    """更新日志级别"""
    if not current_user.is_administrator():
        abort(403, "权限不足")

    data = request.get_json()
    if not data or 'logger_name' not in data or 'level' not in data:
        abort(400, "请提供有效的参数")

    try:
        log_manager.set_level(
            name=data['logger_name'],
            level=data['level'],
            handler_type=data.get('handler_type', 'both')
        )
        return jsonify({"message": "日志级别更新成功"})
    except ValueError as e:
        abort(404, str(e))
    except Exception as e:
        abort(500, str(e))

@router.route('/api/logs/debug', methods=['GET'])
@login_required
def debug_logs():
    """调试日志查询功能"""
    if not current_user.is_administrator():
        abort(403, "权限不足")

    try:
        logger_name = request.args.get('logger_name', 'app')
        limit = int(request.args.get('limit', 10))

        debug_info = log_manager.debug_log_query(name=logger_name, limit=limit)
        return jsonify(debug_info)
    except Exception as e:
        abort(500, f"调试失败: {str(e)}")