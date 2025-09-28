from flask import Blueprint, jsonify, Response, stream_with_context
from flask_jwt_extended import jwt_required
from app.services.system_service import SystemService
import json
import time

system_bp = Blueprint('system', __name__)
service = SystemService()

@system_bp.route('/system/resources', methods=['GET'])
@jwt_required()
def get_resources():
    try:
        data = service.get_resources()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@system_bp.route('/system/resources/stream', methods=['GET'])
@jwt_required()
def stream_resources():
    def event_stream():
        while True:
            try:
                data = service.get_resources()
                # Formato SSE: 'data: <json>\n\n'
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            time.sleep(2)  # intervalo de atualização em segundos
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    }
    return Response(stream_with_context(event_stream()), headers=headers)
