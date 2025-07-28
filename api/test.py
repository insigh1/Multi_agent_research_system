"""
Simple test API endpoint for Vercel
"""

def handler(event, context):
    """Simple handler for testing"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': '{"status": "ok", "message": "API is working", "timestamp": "' + str(__import__('datetime').datetime.now()) + '"}'
    } 