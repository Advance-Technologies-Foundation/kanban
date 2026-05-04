#!/usr/bin/env node
/**
 * Build script: concatenates src/ files into Kanban/Files/src/kanban-min.js and kanban-min.css
 *
 * JS build order matters — all Ext.define files are injected inside the KanbanSection define wrapper,
 * before its `return {` statement. KanbanBoardViewGenerator keeps its own define() call nested inside.
 *
 * Run: node build.js
 * Watch: node build.js --watch
 */

const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const SRC = path.join(ROOT, "src");
const OUT = path.join(ROOT, "Kanban/Files/src");

// Files injected INSIDE the KanbanSection define wrapper, in this order
const JS_INNER = [
	"CaseDataStorage.js",
	"CollectionDataStorage.js",
	"KanbanBoard.js",
	"KanbanBoardViewGenerator.js",
	"KanbanColumn.js",
	"KanbanColumnViewConfigBuilder.js",
	"KanbanColumnViewModel.js",
	"KanbanElement.js",
	"KanbanElementViewModel.js",
];

const CSS_FILES = [
	"css/KanbanElement.css",
	"css/KanbanColumn.css",
	"css/KanbanBoard.css",
];

function read(file) {
	return fs.readFileSync(file, "utf8");
}

function buildJS() {
	const wrapper = read(path.join(SRC, "KanbanSection.js"));

	// KanbanSection.js source deps don't include MainHeaderSchema — add it for the bundle
	const patchedWrapper = wrapper.replace(
		'define("KanbanSection", ["PageUtilities", "ConfigurationEnums", "GridUtilities", "DcmStageViewModel", "DcmStageContainer"]',
		'define("KanbanSection", ["PageUtilities", "ConfigurationEnums", "GridUtilities", "DcmStageViewModel", "DcmStageContainer", "MainHeaderSchema"]'
	);

	// Injection point: the `\treturn {` line that starts the mixin object
	const returnIndex = patchedWrapper.indexOf("\treturn {");
	if (returnIndex === -1) {
		throw new Error("Could not find injection point (\\treturn {) in KanbanSection.js");
	}

	const inner = JS_INNER.map((f) => {
		const content = read(path.join(SRC, f));
		return `\n/* === ${f} === */\n${content}`;
	}).join("\n");

	const output =
		patchedWrapper.slice(0, returnIndex) +
		inner +
		"\n" +
		patchedWrapper.slice(returnIndex);

	fs.writeFileSync(path.join(OUT, "kanban-min.js"), output, "utf8");
	console.log(`[JS]  Kanban/Files/src/kanban-min.js (${output.length} bytes)`);
}

function buildCSS() {
	const output = CSS_FILES.map((f) => {
		const content = read(path.join(SRC, f));
		return `/* === ${path.basename(f)} === */\n${content}`;
	}).join("\n");

	fs.writeFileSync(path.join(OUT, "kanban-min.css"), output, "utf8");
	console.log(`[CSS] Kanban/Files/src/kanban-min.css (${output.length} bytes)`);
}

function build() {
	try {
		buildJS();
		buildCSS();
		console.log("Build OK");
	} catch (err) {
		console.error("Build FAILED:", err.message);
		process.exit(1);
	}
}

build();

if (process.argv.includes("--watch")) {
	const watchDirs = [SRC, path.join(SRC, "css")];
	watchDirs.forEach((dir) => {
		fs.watch(dir, { recursive: false }, (event, filename) => {
			if (!filename || (!filename.endsWith(".js") && !filename.endsWith(".css"))) return;
			console.log(`[watch] ${filename} changed — rebuilding…`);
			build();
		});
	});
	console.log("Watching src/ for changes (Ctrl+C to stop)…");
}
