#!/usr/bin/env node
/** ResQFlow-Flood offline benchmarks (delegates to Python). */
"use strict";
const { execSync } = require("child_process");
const path = require("path");
const script = path.join(__dirname, "run_flood_benchmark.py");
execSync(`python3 "${script}"`, { stdio: "inherit" });
