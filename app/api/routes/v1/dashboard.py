from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from app.services.monitoring import system_monitor
import json
from datetime import datetime
import subprocess
import sys
import os

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def run_self_healing_test():
    """Run the self-healing test in a background task"""
    try:
        python_executable = sys.executable
        script_path = os.path.join(os.getcwd(), "test_ai_integration.py")
        subprocess.run(
            [python_executable, script_path, "self-healing"],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        print(f"Error running self-healing test: {str(e)}")


@router.post("/run-self-healing-test")
async def trigger_self_healing_test(background_tasks: BackgroundTasks):
    """
    Triggers the self-healing test in the background
    """
    try:
        background_tasks.add_task(run_self_healing_test)
        return {
            "status": "success",
            "message": "Self-healing test started in background",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error triggering self-healing test: {str(e)}"
        )


@router.get("/monitoring", response_class=HTMLResponse)
async def get_monitoring_dashboard():
    """
    Renders a dashboard with system monitoring information.
    Displays metrics like request counts, error rates, and system health.
    """
    try:
        # Get monitoring data
        system_monitor.print_summary()

        # Get statistics for HTML display
        stats = system_monitor.get_service_stats()

        # Format the monitoring data for display
        uptime = system_monitor._format_duration(
            (datetime.now() - system_monitor.start_time).total_seconds()
        )
        total_requests = sum(service["requests"] for service in stats)
        error_rate = system_monitor.get_error_rate()
        retry_rate = system_monitor.get_retry_rate()
        avg_response_time = system_monitor.get_avg_response_time()

        # Get recent errors and retries
        recent_errors = system_monitor.errors[-5:] if system_monitor.errors else []
        recent_retries = system_monitor.retries[-5:] if system_monitor.retries else []

        # Build HTML response
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Monitoring Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                .card {{
                    background: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    padding: 20px;
                    margin-bottom: 20px;
                }}
                .metric {{
                    display: inline-block;
                    text-align: center;
                    margin: 10px;
                    min-width: 150px;
                }}
                .metric .value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #3498db;
                }}
                .metric .label {{
                    font-size: 14px;
                    color: #7f8c8d;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .error {{
                    color: #e74c3c;
                }}
                .retry {{
                    color: #f39c12;
                }}
                .button {{
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-right: 10px;
                }}
                .refresh {{
                    float: right;
                }}
                .button:hover {{
                    background: #2980b9;
                }}
                .button.test {{
                    background: #e67e22;
                }}
                .button.test:hover {{
                    background: #d35400;
                }}
                .actions {{
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="actions">
                <button class="button refresh" onclick="location.reload()">Refresh Data</button>
                <button class="button test" onclick="runSelfHealingTest()">Run Self-Healing Test</button>
            </div>
            <h1>System Monitoring Dashboard</h1>
            <div class="card">
                <h2>System Overview</h2>
                <div>
                    <div class="metric">
                        <div class="value">{uptime}</div>
                        <div class="label">Uptime</div>
                    </div>
                    <div class="metric">
                        <div class="value">{total_requests}</div>
                        <div class="label">Total Requests</div>
                    </div>
                    <div class="metric">
                        <div class="value">{error_rate:.2f}%</div>
                        <div class="label">Error Rate</div>
                    </div>
                    <div class="metric">
                        <div class="value">{retry_rate:.2f}%</div>
                        <div class="label">Retry Rate</div>
                    </div>
                    <div class="metric">
                        <div class="value">{avg_response_time:.2f}s</div>
                        <div class="label">Avg Response Time</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Service Statistics</h2>
                <table>
                    <tr>
                        <th>Service</th>
                        <th>Requests</th>
                        <th>Success</th>
                        <th>Errors</th>
                        <th>Retries</th>
                        <th>Error Rate</th>
                        <th>Avg Time</th>
                    </tr>
                    {"".join([f"""<tr>
                        <td>{service['name']}</td>
                        <td>{service['requests']}</td>
                        <td>{service['success']}</td>
                        <td>{service['errors']}</td>
                        <td>{service['retries']}</td>
                        <td>{service['error_rate']:.2f}%</td>
                        <td>{service['avg_time']:.2f}s</td>
                    </tr>""" for service in stats])}
                </table>
            </div>
            
            <div class="card">
                <h2>Recent Errors</h2>
                {f'<table><tr><th>Time</th><th>Service</th><th>Operation</th><th>Error</th></tr>' +
                ''.join([f"""<tr>
                    <td>{datetime.fromtimestamp(error['timestamp']).strftime('%H:%M:%S')}</td>
                    <td>{error['service']}</td>
                    <td>{error['operation']}</td>
                    <td class="error">{error['message']}</td>
                </tr>""" for error in reversed(recent_errors)]) + '</table>'
                if recent_errors else "<p>No recent errors</p>"}
            </div>
            
            <div class="card">
                <h2>Recent Retries</h2>
                {f'<table><tr><th>Time</th><th>Service</th><th>Operation</th><th>Attempt</th><th>Message</th></tr>' +
                ''.join([f"""<tr>
                    <td>{datetime.fromtimestamp(retry['timestamp']).strftime('%H:%M:%S')}</td>
                    <td>{retry['service']}</td>
                    <td>{retry['operation']}</td>
                    <td>{retry['attempt']}</td>
                    <td class="retry">{retry['message']}</td>
                </tr>""" for retry in reversed(recent_retries)]) + '</table>'
                if recent_retries else "<p>No recent retries</p>"}
            </div>
            
            <script>
                // Auto-refresh the page every 30 seconds
                setTimeout(function() {{
                    location.reload();
                }}, 30000);
                
                // Function to run self-healing test
                function runSelfHealingTest() {{
                    fetch('/api/v1/dashboard/run-self-healing-test', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        alert('Self-healing test started. The dashboard will refresh to show results.');
                        setTimeout(() => location.reload(), 5000);
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                        alert('Error starting self-healing test. Check console for details.');
                    }});
                }}
            </script>
        </body>
        </html>
        """

        return html
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating monitoring dashboard: {str(e)}"
        )


@router.get("/metrics")
async def get_monitoring_metrics():
    """
    Returns JSON metrics data for the system monitoring
    """
    try:
        stats = system_monitor.get_service_stats()
        uptime = (datetime.now() - system_monitor.start_time).total_seconds()

        metrics = {
            "system": {
                "uptime": uptime,
                "uptime_formatted": system_monitor._format_duration(uptime),
                "total_requests": sum(service["requests"] for service in stats),
                "error_rate": system_monitor.get_error_rate(),
                "retry_rate": system_monitor.get_retry_rate(),
                "avg_response_time": system_monitor.get_avg_response_time(),
            },
            "services": stats,
            "recent_errors": (
                system_monitor.errors[-5:] if system_monitor.errors else []
            ),
            "recent_retries": (
                system_monitor.retries[-5:] if system_monitor.retries else []
            ),
        }

        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving monitoring metrics: {str(e)}"
        )
