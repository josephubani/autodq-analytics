const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');

const CELL_MARKER = /^\s*(?:#|--)\s*%%(?:\s*\[(.*?)\]|\s+(.*?))?\s*$/;

function splitCells(source) {
  const lines = source.split(/\r?\n/);
  const markers = [];
  lines.forEach((line, index) => {
    const match = CELL_MARKER.exec(line);
    if (match) {
      markers.push({ index, title: (match[1] || match[2] || '').trim() });
    }
  });

  if (!markers.length) {
    const clean = lines.filter((line, index) => !(index === 0 && line.startsWith('#!'))).join('\n');
    return [{ title: 'Script', source: clean, markerLine: 0 }];
  }

  const cells = [];
  const preamble = lines.slice(0, markers[0].index).filter((line) => !line.trim().startsWith('#!'));
  if (preamble.some((line) => line.trim() && !line.trim().startsWith('#') && !line.trim().startsWith('--'))) {
    cells.push({ title: 'Preamble', source: preamble.join('\n'), markerLine: 0 });
  }

  markers.forEach((marker, index) => {
    const next = index + 1 < markers.length ? markers[index + 1].index : lines.length;
    cells.push({
      title: marker.title || `Cell ${cells.length + 1}`,
      source: lines.slice(marker.index + 1, next).join('\n'),
      markerLine: marker.index
    });
  });
  return cells;
}

function shellQuote(value) {
  if (process.platform === 'win32') {
    return `"${String(value).replace(/"/g, '\\"')}"`;
  }
  return `'${String(value).replace(/'/g, `'"'"'`)}'`;
}

function commandPath(resource) {
  const configured = vscode.workspace.getConfiguration('autodq').get('commandPath', '').trim();
  if (configured) {
    return configured;
  }

  const folder = resource && vscode.workspace.getWorkspaceFolder(resource);
  if (folder) {
    const candidates = process.platform === 'win32'
      ? [path.join(folder.uri.fsPath, '.venv', 'Scripts', 'autodq.exe')]
      : [path.join(folder.uri.fsPath, '.venv', 'bin', 'autodq')];
    const localCommand = candidates.find((candidate) => fs.existsSync(candidate));
    if (localCommand) {
      return localCommand;
    }
  }

  return 'autodq';
}

function runInTerminal(document, args = []) {
  const terminal = vscode.window.createTerminal({ name: 'AutoDQ ADQL', cwd: path.dirname(document.uri.fsPath) });
  const command = [commandPath(document.uri), 'run', document.uri.fsPath, ...args].map(shellQuote).join(' ');
  terminal.show();
  terminal.sendText(command);
}

class ADQLCodeLensProvider {
  provideCodeLenses(document) {
    const cells = splitCells(document.getText());
    const lenses = [];
    cells.forEach((cell, index) => {
      const line = Math.min(cell.markerLine, Math.max(0, document.lineCount - 1));
      const range = new vscode.Range(line, 0, line, 0);
      lenses.push(new vscode.CodeLens(range, {
        title: '$(run) Run through cell',
        command: 'autodq.adql.runThroughCell',
        arguments: [document, index + 1]
      }));
      lenses.push(new vscode.CodeLens(range, {
        title: 'Run cell only',
        command: 'autodq.adql.runCellOnly',
        arguments: [document, index + 1]
      }));
    });
    return lenses;
  }
}

class ADQLSymbolProvider {
  provideDocumentSymbols(document) {
    return splitCells(document.getText()).map((cell) => {
      const line = Math.min(cell.markerLine, Math.max(0, document.lineCount - 1));
      const range = document.lineAt(line).range;
      return new vscode.DocumentSymbol(cell.title, 'ADQL cell', vscode.SymbolKind.Namespace, range, range);
    });
  }
}

class ADQLNotebookSerializer {
  async deserializeNotebook(content) {
    const text = new TextDecoder().decode(content);
    const notebookCells = splitCells(text).map((cell) => {
      const data = new vscode.NotebookCellData(vscode.NotebookCellKind.Code, cell.source, 'adql');
      data.metadata = { title: cell.title };
      return data;
    });
    return new vscode.NotebookData(notebookCells);
  }

  async serializeNotebook(data) {
    const sections = ['#!/usr/bin/env autodq'];
    data.cells.forEach((cell, index) => {
      const title = (cell.metadata && cell.metadata.title) || `Cell ${index + 1}`;
      sections.push(`# %% [${title}]`);
      sections.push(cell.value.replace(/\s+$/, ''));
    });
    return new TextEncoder().encode(`${sections.join('\n')}\n`);
  }
}

async function executeNotebookCells(cells, notebook) {
  if (notebook.isUntitled) {
    vscode.window.showErrorMessage('Save the .adql file before running it.');
    return;
  }
  await notebook.save();

  for (const cell of cells) {
    const execution = controller.createNotebookCellExecution(cell);
    const cellNumber = notebook.getCells().findIndex((item) => item === cell) + 1;
    execution.start(Date.now());
    execution.executionOrder = cellNumber;

    await new Promise((resolve) => {
      const args = ['run', notebook.uri.fsPath, '--through-cell', String(cellNumber)];
      const child = execFile(commandPath(notebook.uri), args, { cwd: path.dirname(notebook.uri.fsPath) }, (error, stdout, stderr) => {
        const output = [stdout, stderr].filter(Boolean).join('\n').trim();
        execution.replaceOutput([
          new vscode.NotebookCellOutput([
            vscode.NotebookCellOutputItem.text(output || (error ? String(error) : 'ADQL cell completed.'), 'text/plain')
          ])
        ]);
        execution.end(!error, Date.now());
        resolve();
      });
      execution.token.onCancellationRequested(() => child.kill());
    });
  }
}

let controller;

function activate(context) {
  const selector = { language: 'adql', scheme: 'file' };
  context.subscriptions.push(vscode.languages.registerCodeLensProvider(selector, new ADQLCodeLensProvider()));
  context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider(selector, new ADQLSymbolProvider()));
  context.subscriptions.push(vscode.workspace.registerNotebookSerializer(
    'autodq-adql-notebook',
    new ADQLNotebookSerializer(),
    { transientOutputs: true }
  ));

  controller = vscode.notebooks.createNotebookController(
    'autodq-adql-kernel',
    'autodq-adql-notebook',
    'AutoDQ ADQL'
  );
  controller.supportedLanguages = ['adql'];
  controller.supportsExecutionOrder = true;
  controller.executeHandler = executeNotebookCells;
  context.subscriptions.push(controller);

  context.subscriptions.push(vscode.commands.registerCommand('autodq.adql.runFile', async () => {
    const document = vscode.window.activeTextEditor && vscode.window.activeTextEditor.document;
    if (!document || document.languageId !== 'adql') {
      vscode.window.showErrorMessage('Open an .adql file first.');
      return;
    }
    await document.save();
    runInTerminal(document);
  }));
  context.subscriptions.push(vscode.commands.registerCommand('autodq.adql.runThroughCell', async (document, number) => {
    await document.save();
    runInTerminal(document, ['--through-cell', String(number)]);
  }));
  context.subscriptions.push(vscode.commands.registerCommand('autodq.adql.runCellOnly', async (document, number) => {
    await document.save();
    runInTerminal(document, ['--cell', String(number)]);
  }));
}

function deactivate() {}

module.exports = { activate, deactivate, splitCells };
