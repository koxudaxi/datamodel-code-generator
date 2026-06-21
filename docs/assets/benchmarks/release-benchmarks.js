(function () {
  "use strict";

  const STATUS_OK = "ok";
  const FORMATTERS = [
    { key: "default", label: "Default", color: "#6b7280" },
    { key: "builtin", label: "Built-in", color: "#2563eb" },
    { key: "ruff", label: "Ruff", color: "#16a34a" },
  ];

  const charts = Array.from(document.querySelectorAll("[data-release-benchmark-chart]"));
  if (charts.length === 0) {
    return;
  }

  const scriptUrl = document.currentScript ? document.currentScript.src : document.baseURI;
  const dataUrl = new URL("../../data/release-benchmarks.json", scriptUrl);

  function versionKey(version) {
    const parts = String(version)
      .replace(/^v/, "")
      .split(/[.\-+_]/)
      .map((part) => (/^\d+$/.test(part) ? Number(part) : 0));
    while (parts.length < 4) {
      parts.push(0);
    }
    return parts;
  }

  function compareVersions(left, right) {
    const leftKey = versionKey(left);
    const rightKey = versionKey(right);
    for (let index = 0; index < 4; index += 1) {
      if (leftKey[index] !== rightKey[index]) {
        return leftKey[index] - rightKey[index];
      }
    }
    return String(left).localeCompare(String(right));
  }

  function formatMs(value) {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}s`;
    }
    if (value >= 100) {
      return `${value.toFixed(0)}ms`;
    }
    if (value >= 10) {
      return `${value.toFixed(1)}ms`;
    }
    return `${value.toFixed(2)}ms`;
  }

  function inputLabel(inputType) {
    switch (inputType) {
      case "openapi":
        return "OpenAPI";
      case "jsonschema":
        return "JSON Schema";
      default:
        return inputType;
    }
  }

  function findEntry(entries, version, formatter) {
    return entries.find(
      (entry) =>
        entry.version === version &&
        entry.formatter === formatter &&
        entry.status === STATUS_OK &&
        typeof entry.median_ms === "number",
    );
  }

  function scale(value, sourceMin, sourceMax, targetMin, targetMax) {
    if (sourceMax === sourceMin) {
      return (targetMin + targetMax) / 2;
    }
    return targetMin + ((value - sourceMin) / (sourceMax - sourceMin)) * (targetMax - targetMin);
  }

  function cssColor(element, name, fallback) {
    const value = getComputedStyle(element).getPropertyValue(name).trim();
    return value || fallback;
  }

  function scenarioEntries(data, inputType, caseName) {
    return data.entries.filter((entry) => entry.input_type === inputType && entry.case === caseName);
  }

  function renderLegend(container) {
    const legend = container.querySelector(".release-benchmark-chart__legend");
    if (!legend) {
      return;
    }
    legend.innerHTML = FORMATTERS.map(
      (formatter) =>
        `<span class="release-benchmark-chart__legend-item"><span class="release-benchmark-chart__swatch" style="background:${formatter.color}"></span>${formatter.label}</span>`,
    ).join("");
  }

  function chartSize(canvas) {
    const rect = canvas.getBoundingClientRect();
    const style = getComputedStyle(canvas);
    const width = Math.max(320, Math.floor(rect.width));
    const height = Math.max(260, Number.parseFloat(style.height) || 420);
    return { width, height };
  }

  function isVisible(element) {
    return Boolean(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
  }

  function drawChart(container, data) {
    const canvas = container.querySelector("canvas");
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }
    if (!isVisible(container)) {
      return;
    }

    const inputType = container.dataset.inputType || "";
    const caseName = container.dataset.case || "";
    const entries = scenarioEntries(data, inputType, caseName);
    const versions = Array.from(new Set(entries.map((entry) => entry.version))).sort(compareVersions);
    const okEntries = entries.filter((entry) => entry.status === STATUS_OK && typeof entry.median_ms === "number");

    if (versions.length === 0 || okEntries.length === 0) {
      return;
    }

    const { width, height } = chartSize(canvas);
    const devicePixelRatio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * devicePixelRatio);
    canvas.height = Math.floor(height * devicePixelRatio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    context.clearRect(0, 0, width, height);

    const foreground = cssColor(container, "--md-default-fg-color", "#111827");
    const muted = cssColor(container, "--md-default-fg-color--light", "#6b7280");
    const grid = cssColor(container, "--md-default-fg-color--lightest", "#d1d5db");
    const plot = {
      left: 58,
      top: 38,
      right: width - 18,
      bottom: height - 58,
    };
    const maxMs = Math.max(...okEntries.map((entry) => entry.median_ms || 0));
    const yMax = maxMs > 0 ? maxMs * 1.15 : 1;
    const points = [];

    context.font = "12px system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";
    context.fillStyle = foreground;
    context.fillText(`${caseName[0].toUpperCase()}${caseName.slice(1)} / ${inputLabel(inputType)}`, plot.left, 20);

    context.strokeStyle = grid;
    context.fillStyle = muted;
    context.lineWidth = 1;
    for (let index = 0; index <= 4; index += 1) {
      const value = (yMax * index) / 4;
      const y = scale(value, 0, yMax, plot.bottom, plot.top);
      context.beginPath();
      context.moveTo(plot.left, y);
      context.lineTo(plot.right, y);
      context.stroke();
      context.textAlign = "right";
      context.fillText(formatMs(value), plot.left - 10, y + 4);
    }

    const tickStep = Math.max(1, Math.round(versions.length / 8));
    context.textAlign = "center";
    versions.forEach((version, index) => {
      if (index % tickStep !== 0 && index !== versions.length - 1) {
        return;
      }
      const x = scale(index, 0, Math.max(versions.length - 1, 1), plot.left, plot.right);
      context.strokeStyle = grid;
      context.beginPath();
      context.moveTo(x, plot.top);
      context.lineTo(x, plot.bottom);
      context.stroke();
      context.fillStyle = muted;
      context.fillText(version, x, plot.bottom + 24);
    });

    context.strokeStyle = foreground;
    context.beginPath();
    context.moveTo(plot.left, plot.top);
    context.lineTo(plot.left, plot.bottom);
    context.lineTo(plot.right, plot.bottom);
    context.stroke();

    FORMATTERS.forEach((formatter) => {
      const formatterPoints = [];
      versions.forEach((version, index) => {
        const entry = findEntry(entries, version, formatter.key);
        if (!entry) {
          return;
        }
        const x = scale(index, 0, Math.max(versions.length - 1, 1), plot.left, plot.right);
        const y = scale(entry.median_ms, 0, yMax, plot.bottom, plot.top);
        formatterPoints.push({ x, y, entry, formatter });
        points.push({ x, y, entry, formatter });
      });
      if (formatterPoints.length === 0) {
        return;
      }
      context.strokeStyle = formatter.color;
      context.lineWidth = 2.4;
      context.beginPath();
      formatterPoints.forEach((point, index) => {
        if (index === 0) {
          context.moveTo(point.x, point.y);
          return;
        }
        context.lineTo(point.x, point.y);
      });
      context.stroke();

      context.fillStyle = formatter.color;
      formatterPoints.forEach((point) => {
        context.beginPath();
        context.arc(point.x, point.y, 3, 0, Math.PI * 2);
        context.fill();
      });
    });

    container.releaseBenchmarkPoints = points;
  }

  function showTooltip(container, event) {
    const tooltip = container.querySelector(".release-benchmark-chart__tooltip");
    const canvas = container.querySelector("canvas");
    if (!tooltip || !(canvas instanceof HTMLCanvasElement) || !container.releaseBenchmarkPoints) {
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    let nearest = null;
    let nearestDistance = 14;
    container.releaseBenchmarkPoints.forEach((point) => {
      const distance = Math.hypot(point.x - x, point.y - y);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    });
    if (!nearest) {
      tooltip.hidden = true;
      return;
    }
    tooltip.textContent = `${nearest.entry.version} · ${nearest.formatter.label}: ${formatMs(nearest.entry.median_ms)}`;
    tooltip.style.left = `${canvas.offsetLeft + nearest.x}px`;
    tooltip.style.top = `${canvas.offsetTop + nearest.y}px`;
    tooltip.hidden = false;
  }

  function hideTooltip(container) {
    const tooltip = container.querySelector(".release-benchmark-chart__tooltip");
    if (tooltip) {
      tooltip.hidden = true;
    }
  }

  function renderAll(data) {
    charts.forEach((container) => drawChart(container, data));
  }

  fetch(dataUrl)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Could not load ${dataUrl.pathname}`);
      }
      return response.json();
    })
    .then((data) => {
      charts.forEach((container) => {
        renderLegend(container);
        container.addEventListener("mousemove", (event) => showTooltip(container, event));
        container.addEventListener("mouseleave", () => hideTooltip(container));
      });
      renderAll(data);
      const observer = new ResizeObserver(() => window.requestAnimationFrame(() => renderAll(data)));
      charts.forEach((container) => observer.observe(container));
      document.addEventListener("click", () => window.setTimeout(() => renderAll(data), 50));
    })
    .catch((error) => {
      charts.forEach((container) => {
        const tooltip = container.querySelector(".release-benchmark-chart__tooltip");
        if (tooltip) {
          tooltip.textContent = error.message;
          tooltip.hidden = false;
        }
      });
    });
})();
