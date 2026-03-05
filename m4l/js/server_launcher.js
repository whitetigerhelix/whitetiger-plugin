/**
 * server_launcher.js — Node.js script for Max's `node.script` object.
 *
 * Spawns and manages the Python FastAPI service as a child process.
 * The child process is tied to Max's lifecycle — it dies when Max closes.
 *
 * Outlets:
 *   0: Status string (stopped/starting/running/error: ...)
 *   1: Server stdout/stderr (debug)
 *
 * Messages:
 *   start              — spawn the service
 *   stop               — graceful shutdown via /shutdown endpoint, force-kill fallback
 *   status             — report current state
 *   service_dir <path> — set path to service/ directory
 *   python_path <path> — override Python executable path
 *   port <number>      — set service port (default 8787)
 *
 * Canonical reference: Docs/Plan_Server_Management.md
 */

const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const Max = require("max-api");

let serverProcess = null;
let currentState = "stopped"; // stopped | starting | running | error
let serviceDir = "";
let pythonPath = "";
let servicePort = 8787;

function setState(state, detail) {
  currentState = state;
  const msg = detail ? state + ": " + detail : state;
  Max.outlet(0, msg);
}

// --- Auto-detect paths ---

function resolveServiceDir() {
  if (serviceDir) return serviceDir;
  // Try relative to this script: m4l/js/../../../service
  const guess = path.resolve(__dirname, "..", "..", "service");
  return guess;
}

function resolvePythonPath() {
  if (pythonPath) return pythonPath;
  const dir = resolveServiceDir();
  // Windows venv path
  const winPath = path.join(dir, ".venv", "Scripts", "python.exe");
  try {
    require("fs").accessSync(winPath);
    return winPath;
  } catch (e) {}
  // Unix venv path
  const unixPath = path.join(dir, ".venv", "bin", "python");
  try {
    require("fs").accessSync(unixPath);
    return unixPath;
  } catch (e) {}
  return "python";
}

// --- Health polling ---

function pollHealth(attemptsLeft, callback) {
  if (attemptsLeft <= 0) {
    callback(false);
    return;
  }

  const req = http.get(
    "http://127.0.0.1:" + servicePort + "/health",
    function (res) {
      let data = "";
      res.on("data", function (chunk) {
        data += chunk;
      });
      res.on("end", function () {
        try {
          const obj = JSON.parse(data);
          if (obj.ok) {
            callback(true);
            return;
          }
        } catch (e) {}
        setTimeout(function () {
          pollHealth(attemptsLeft - 1, callback);
        }, 1000);
      });
    },
  );
  req.on("error", function () {
    setTimeout(function () {
      pollHealth(attemptsLeft - 1, callback);
    }, 1000);
  });
  req.setTimeout(2000, function () {
    req.destroy();
    setTimeout(function () {
      pollHealth(attemptsLeft - 1, callback);
    }, 1000);
  });
}

// --- Message handlers ---

Max.addHandler("service_dir", function (dir) {
  serviceDir = String(dir);
  Max.post("server_launcher: service_dir = " + serviceDir);
});

Max.addHandler("python_path", function (p) {
  pythonPath = String(p);
  Max.post("server_launcher: python_path = " + pythonPath);
});

Max.addHandler("port", function (p) {
  servicePort = parseInt(p) || 8787;
  Max.post("server_launcher: port = " + servicePort);
});

Max.addHandler("status", function () {
  Max.outlet(0, currentState);
});

Max.addHandler("start", function () {
  if (serverProcess) {
    setState("running", "already running");
    return;
  }

  const dir = resolveServiceDir();
  const python = resolvePythonPath();

  Max.post("server_launcher: starting service...");
  Max.post("  dir: " + dir);
  Max.post("  python: " + python);
  Max.post("  port: " + servicePort);

  setState("starting");

  try {
    serverProcess = spawn(
      python,
      [
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        "127.0.0.1",
        "--port",
        String(servicePort),
      ],
      {
        cwd: dir,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
  } catch (e) {
    setState("error", "spawn failed: " + e.message);
    serverProcess = null;
    return;
  }

  serverProcess.stdout.on("data", function (data) {
    Max.outlet(1, String(data).trim());
  });

  serverProcess.stderr.on("data", function (data) {
    Max.outlet(1, String(data).trim());
  });

  serverProcess.on("error", function (err) {
    setState("error", err.message);
    serverProcess = null;
  });

  serverProcess.on("exit", function (code) {
    Max.post("server_launcher: process exited with code " + code);
    serverProcess = null;
    setState("stopped");
  });

  // Poll /health to confirm it's actually responding
  pollHealth(15, function (ok) {
    if (ok) {
      setState("running");
    } else if (serverProcess) {
      setState("error", "started but not responding after 15s");
    }
  });
});

Max.addHandler("stop", function () {
  if (!serverProcess) {
    setState("stopped");
    return;
  }

  setState("stopping");

  // Try graceful shutdown via HTTP
  const postData = "{}";
  const req = http.request(
    {
      hostname: "127.0.0.1",
      port: servicePort,
      path: "/shutdown",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
      timeout: 3000,
    },
    function () {
      // Response received — server is shutting down
      // Wait a moment, then force-kill if still alive
      setTimeout(function () {
        if (serverProcess) {
          try {
            serverProcess.kill("SIGTERM");
          } catch (e) {}
          serverProcess = null;
          setState("stopped");
        }
      }, 2000);
    },
  );

  req.on("error", function () {
    // Shutdown endpoint failed — force kill
    if (serverProcess) {
      try {
        serverProcess.kill("SIGTERM");
      } catch (e) {}
      serverProcess = null;
    }
    setState("stopped");
  });

  req.on("timeout", function () {
    req.destroy();
    if (serverProcess) {
      try {
        serverProcess.kill("SIGTERM");
      } catch (e) {}
      serverProcess = null;
    }
    setState("stopped");
  });

  req.write(postData);
  req.end();
});

// Safety net: kill child when Node exits
process.on("exit", function () {
  if (serverProcess) {
    try {
      serverProcess.kill("SIGTERM");
    } catch (e) {}
  }
});
