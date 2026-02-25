import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
	let currentPanel: vscode.WebviewPanel | undefined = undefined;

	const disposable = vscode.commands.registerCommand('atp-guardian.startClient', () => {
		if (currentPanel) {
			currentPanel.reveal(vscode.ViewColumn.Two);
		} else {
			currentPanel = vscode.window.createWebviewPanel(
				'atpGuardian',
				'ATP Guardian - Live Execution Log',
				vscode.ViewColumn.Two,
				{ enableScripts: true }
			);

			currentPanel.webview.html = getWebviewContent();

			currentPanel.onDidDispose(() => {
				currentPanel = undefined;
			}, null, context.subscriptions);
		}
	});

	context.subscriptions.push(disposable);
}

function getWebviewContent() {
	return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATP Guardian</title>
    <style>
        body { font-family: sans-serif; padding: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid var(--vscode-panel-border); padding: 8px; text-align: left; }
        th { background-color: var(--vscode-editor-inactiveSelectionBackground); }
        .anomaly { background-color: rgba(255, 0, 0, 0.2); border-left: 4px solid red; }
        pre { margin: 0; white-space: pre-wrap; font-size: 12px; }
    </style>
</head>
<body>
    <h2>Agent Execution Trace</h2>
    <p>Monitoring local interactions natively...</p>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Framework</th>
                <th>Tool</th>
                <th>Arguments</th>
                <th>Result</th>
            </tr>
        </thead>
        <tbody id="logs-body">
            <tr><td colspan="5">Loading logs...</td></tr>
        </tbody>
    </table>

    <script>
        async function fetchLogs() {
            try {
                const response = await fetch('http://127.0.0.1:8000/logs');
                const logs = await response.json();
                
                const tbody = document.getElementById('logs-body');
                tbody.innerHTML = '';
                
                if (logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5">No logs recorded yet.</td></tr>';
                    return;
                }

                logs.forEach(log => {
                    const row = document.createElement('tr');
                    if (log.is_anomaly) {
                        row.className = 'anomaly';
                    }
                    
                    const timeCell = document.createElement('td');
                    timeCell.textContent = new Date(log.timestamp).toLocaleTimeString();
                    
                    const fwCell = document.createElement('td');
                    fwCell.textContent = log.agent_framework;
                    
                    const toolCell = document.createElement('td');
                    toolCell.textContent = log.tool_name;
                    
                    const argsCell = document.createElement('td');
                    argsCell.innerHTML = '<pre>' + JSON.stringify(log.input_arguments, null, 2) + '</pre>';
                    
                    const resCell = document.createElement('td');
                    resCell.innerHTML = '<pre>' + (log.execution_result || 'N/A') + '</pre>';
                    
                    row.appendChild(timeCell);
                    row.appendChild(fwCell);
                    row.appendChild(toolCell);
                    row.appendChild(argsCell);
                    row.appendChild(resCell);
                    
                    tbody.appendChild(row);
                });
            } catch (err) {
                console.error("Failed to fetch logs:", err);
            }
        }

        // Poll every 3 seconds
        setInterval(fetchLogs, 3000);
        fetchLogs();
    </script>
</body>
</html>`;
}

export function deactivate() { }
