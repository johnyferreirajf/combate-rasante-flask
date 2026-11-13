"""API de snapshots para sync GIS; NÃO realiza merge automático de edições.

GET /api/app/gis-sync/<collection>
PUT /api/app/gis-sync/<collection>  {"base_version": N, "items": [...]}

Coleções: gis (itens: {talhoes:[], waypoints:[]}) e flight_areas (itens: []).
A versão deve ser obtida via GET; divergência gera 409, nunca sobrescreve.
"""
from datetime import timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.gis_sync_snapshot import GisSyncSnapshot
from app.routes.mobile_api import _bearer_token, _firebase_identity


gis_sync_bp = Blueprint('gis_sync_api', __name__, url_prefix='/api/app/gis-sync')
_MAX_BYTES = 2 * 1024 * 1024
_COLLECTIONS = {'gis', 'flight_areas'}


def _identity():
    token = _bearer_token()
    if not token:
        return None, (jsonify({'ok': False, 'error': 'missing_token'}), 401)
    identity, error = _firebase_identity(token)
    if error:
        return None, error
    uid = str(identity.get('localId') or '').strip()
    if not uid or len(uid) > 128:
        return None, (jsonify({'ok': False, 'error': 'invalid_firebase_uid'}), 401)
    return uid, None


def _response(record, collection):
    return {
        'ok': True,
        'collection': collection,
        'version': record.version if record else 0,
        'items': record.payload if record else None,
        'updated_at': (
            record.updated_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            if record and record.updated_at else None
        ),
    }


def _validate_payload(collection, value):
    if collection == 'gis':
        if not isinstance(value, dict):
            return False
        if set(value) != {'talhoes', 'waypoints'}:
            return False
        return isinstance(value['talhoes'], list) and isinstance(value['waypoints'], list) and all(
            isinstance(i, dict) for k in ('talhoes', 'waypoints') for i in value[k]
        )
    return isinstance(value, list) and all(isinstance(i, dict) for i in value)


@gis_sync_bp.route('/<collection>', methods=['GET', 'PUT'])
def snapshot(collection):
    if collection not in _COLLECTIONS:
        return jsonify({'ok': False, 'error': 'unsupported_collection'}), 404
    uid, error = _identity()
    if error:
        return error

    if request.method == 'GET':
        record = GisSyncSnapshot.query.filter_by(firebase_uid=uid, collection=collection).first()
        return jsonify(_response(record, collection))

    if request.content_length is not None and request.content_length > _MAX_BYTES:
        return jsonify({'ok': False, 'error': 'payload_too_large'}), 413
    raw = request.get_data(cache=True)
    if len(raw) > _MAX_BYTES:
        return jsonify({'ok': False, 'error': 'payload_too_large'}), 413
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or type(body.get('base_version')) is not int or body['base_version'] < 0:
        return jsonify({'ok': False, 'error': 'invalid_base_version'}), 400
    items = body.get('items')
    if not _validate_payload(collection, items):
        return jsonify({'ok': False, 'error': 'invalid_items'}), 400

    record = GisSyncSnapshot.query.filter_by(firebase_uid=uid, collection=collection).with_for_update().first()
    actual_version = record.version if record else 0
    if body['base_version'] != actual_version:
        return jsonify({'ok': False, 'error': 'version_conflict', **_response(record, collection)}), 409
    if not record:
        record = GisSyncSnapshot(firebase_uid=uid, collection=collection, version=1, payload=items)
        db.session.add(record)
    else:
        record.version += 1
        record.payload = items
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'ok': False, 'error': 'version_conflict'}), 409
    return jsonify(_response(record, collection))
