import json
import os
import sys
from typing import Dict

# Import from the implementation_scripts package
# The Dockerfile ensures the root directory is in PYTHONPATH
try:
    from implementation_scripts.lc_generator_main import run_lc_generator
except ImportError:
    # Fallback for local testing if running from within the lambda folder
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from implementation_scripts.lc_generator_main import run_lc_generator

def handler(event: Dict, context):
    """
    AWS Lambda handler for the Lifecycle Generator.
    The 'event' dictionary should contain the same structure as the config JSON.
    """
    print(f"Lambda received event: {json.dumps(event)}")
    
    try:
        # Run the generator
        result = run_lc_generator(event)
        
        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
    except Exception as e:
        print(f"Error running LC Generator: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e)
            })
        }
