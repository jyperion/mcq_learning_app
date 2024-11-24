from flask import Blueprint, jsonify, current_app
from ..database.db import get_db

bp = Blueprint('stats', __name__, url_prefix='/api/stats')

@bp.route('/overview')
def get_overview_stats():
    """Get overview statistics for the current user"""
    db = get_db()
    try:
        # Get total questions attempted
        total_questions = db.execute(
            'SELECT COUNT(*) as count FROM user_answers'
        ).fetchone()['count']
        
        # Get average score
        avg_score = db.execute(
            'SELECT AVG(CASE WHEN is_correct THEN 100 ELSE 0 END) as avg_score '
            'FROM user_answers'
        ).fetchone()['avg_score'] or 0
        
        # Get total time spent
        total_time = db.execute(
            'SELECT SUM(time_taken) as total_time FROM user_answers'
        ).fetchone()['total_time'] or 0
        
        return jsonify({
            'totalQuestions': total_questions,
            'averageScore': round(avg_score, 2),
            'totalTime': round(total_time / 60)  # Convert to minutes
        })
    except Exception as e:
        current_app.logger.error(f"Error getting overview stats: {str(e)}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@bp.route('/concepts')
def get_concept_stats():
    """Get performance statistics by concept"""
    db = get_db()
    try:
        stats = db.execute(
            'SELECT c.name as concept, '
            'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as score '
            'FROM concepts c '
            'JOIN question_concepts qc ON c.id = qc.concept_id '
            'JOIN user_answers ua ON qc.question_id = ua.question_id '
            'GROUP BY c.id, c.name'
        ).fetchall()
        
        return jsonify({
            'concepts': [row['concept'] for row in stats],
            'scores': [round(row['score'], 2) for row in stats]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting concept stats: {str(e)}")
        return jsonify({'error': 'Failed to get concept statistics'}), 500

@bp.route('/progress')
def get_progress_stats():
    """Get progress statistics over time"""
    db = get_db()
    try:
        progress = db.execute(
            'SELECT DATE(timestamp) as date, '
            'AVG(CASE WHEN is_correct THEN 100 ELSE 0 END) as score '
            'FROM user_answers '
            'GROUP BY DATE(timestamp) '
            'ORDER BY date'
        ).fetchall()
        
        return jsonify({
            'dates': [row['date'] for row in progress],
            'scores': [round(row['score'], 2) for row in progress]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting progress stats: {str(e)}")
        return jsonify({'error': 'Failed to get progress statistics'}), 500

@bp.route('/activity')
def get_recent_activity():
    """Get recent user activity"""
    db = get_db()
    try:
        activity = db.execute(
            'SELECT ua.timestamp as date, '
            'c.name as concept, '
            'CASE WHEN ua.is_correct THEN 100 ELSE 0 END as score, '
            'ua.time_taken as time_spent '
            'FROM user_answers ua '
            'JOIN question_concepts qc ON ua.question_id = qc.question_id '
            'JOIN concepts c ON qc.concept_id = c.id '
            'ORDER BY ua.timestamp DESC '
            'LIMIT 10'
        ).fetchall()
        
        return jsonify([{
            'date': row['date'],
            'concept': row['concept'],
            'score': row['score'],
            'timeSpent': round(row['time_spent'] / 60)  # Convert to minutes
        } for row in activity])
    except Exception as e:
        current_app.logger.error(f"Error getting recent activity: {str(e)}")
        return jsonify({'error': 'Failed to get recent activity'}), 500
