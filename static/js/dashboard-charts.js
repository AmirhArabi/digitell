/**
 * ابزار مشترک نمودارهای پنل مدیریت دیجی تل.
 *
 * پیش‌نیاز: Chart.js (به صورت لوکال در static/js/vendor/chart.umd.min.js بارگذاری می‌شود)
 * استفاده:
 *   ZitroCharts.boot(function () {
 *       ZitroCharts.render('chart-daily', { type: 'line', labels: [...], datasets: [...] });
 *   });
 */
(function (global) {
    'use strict';

    var FONT = "Vazirmatn, 'Segoe UI', sans-serif";
    var numberFormatter = new Intl.NumberFormat('fa-IR');
    var PALETTE = [
        '#2563eb', '#7c3aed', '#0ea5e9', '#14b8a6', '#f59e0b',
        '#ef4444', '#8b5cf6', '#64748b', '#10b981', '#f97316'
    ];

    function num(value) {
        return numberFormatter.format(Math.round(Number(value) || 0));
    }

    function money(value) {
        return num(value) + ' تومان';
    }

    function compact(value) {
        var v = Number(value) || 0;
        var abs = Math.abs(v);
        if (abs >= 1000000000) return num(v / 1000000000) + ' مـیلیارد';
        if (abs >= 1000000) return num(v / 1000000) + ' مـیلیون';
        if (abs >= 1000) return num(v / 1000) + ' هـزار';
        return num(v);
    }

    function formatValue(value, format) {
        if (format === 'money') return money(value);
        if (format === 'compact') return compact(value);
        return num(value);
    }

    function palette(index) {
        return PALETTE[index % PALETTE.length];
    }

    function withAlpha(hex, alpha) {
        var clean = hex.replace('#', '');
        var r = parseInt(clean.substring(0, 2), 16);
        var g = parseInt(clean.substring(2, 4), 16);
        var b = parseInt(clean.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha + ')';
    }

    function applyPalette(dataset, index, total, spec) {
        var color = dataset.color || palette(index);
        var isRadial = spec && (spec.type === 'doughnut' || spec.type === 'pie');
        var isBar = !isRadial && (spec.type === 'bar' || spec.horizontal);

        if (isRadial) {
            dataset.backgroundColor = dataset.backgroundColor
                || (dataset.data || []).map(function (_, pointIndex) { return palette(pointIndex); });
            dataset.borderColor = dataset.borderColor || '#ffffff';
            dataset.borderWidth = dataset.borderWidth === undefined ? 2 : dataset.borderWidth;
        } else if (isBar) {
            dataset.backgroundColor = dataset.backgroundColor || withAlpha(color, dataset.fill ? 0.85 : 0.9);
            dataset.hoverBackgroundColor = dataset.hoverBackgroundColor || color;
            dataset.borderRadius = dataset.borderRadius === undefined ? 7 : dataset.borderRadius;
            dataset.maxBarThickness = dataset.maxBarThickness || 32;
        } else {
            dataset.borderColor = dataset.borderColor || color;
            dataset.backgroundColor = dataset.backgroundColor || withAlpha(color, 0.14);
            dataset.borderWidth = dataset.borderWidth === undefined ? 2.5 : dataset.borderWidth;
            dataset.tension = dataset.tension === undefined ? 0.35 : dataset.tension;
            dataset.pointRadius = dataset.pointRadius === undefined ? 0 : dataset.pointRadius;
            dataset.pointHoverRadius = dataset.pointHoverRadius || 5;
            dataset.pointBackgroundColor = dataset.pointBackgroundColor || color;
            if (dataset.fill === undefined) dataset.fill = total === 1;
        }
        return dataset;
    }

    function tickCallback(format) {
        return function (value) {
            if (format === 'money' || format === 'compact') return compact(value);
            return num(value);
        };
    }

    function baseOptions(spec) {
        var radial = spec.type === 'doughnut' || spec.type === 'pie';
        var horizontal = !!spec.horizontal;

        var options = {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: horizontal ? 'y' : 'x',
            layout: { padding: spec.padding || 0 },
            interaction: { mode: radial ? 'nearest' : 'index', intersect: false },
            plugins: {
                legend: {
                    display: spec.legend !== false,
                    rtl: true,
                    position: radial || spec.legendPosition ? (spec.legendPosition || 'left') : 'bottom',
                    labels: {
                        font: { family: FONT, size: 11 },
                        color: '#64748b',
                        usePointStyle: true,
                        pointStyle: 'circle',
                        boxWidth: 8,
                        boxHeight: 8,
                        padding: radial ? 10 : 16
                    }
                },
                tooltip: {
                    rtl: true,
                    textDirection: 'rtl',
                    backgroundColor: 'rgba(15,23,42,0.94)',
                    titleFont: { family: FONT, size: 11 },
                    bodyFont: { family: FONT, size: 11, weight: '600' },
                    padding: 10,
                    cornerRadius: 10,
                    boxPadding: 5,
                    callbacks: {
                        label: function (context) {
                            var format = context.dataset.format || spec.format || 'number';
                            var label = context.dataset.label ? context.dataset.label + ': ' : '';
                            var raw = horizontal ? context.parsed.x : context.parsed.y;
                            if (raw === null || raw === undefined) raw = context.parsed;
                            return label + formatValue(raw, format);
                        }
                    }
                }
            }
        };

        if (!radial) {
            options.scales = {
                x: {
                    stacked: !!spec.stacked,
                    grid: { display: horizontal, color: '#f1f5f9', drawBorder: false },
                    border: { display: false },
                    ticks: {
                        font: { family: FONT, size: 10 },
                        color: '#94a3b8',
                        maxRotation: horizontal ? 0 : 45,
                        minRotation: 0,
                        autoSkipPadding: 8
                    }
                },
                y: {
                    stacked: !!spec.stacked,
                    beginAtZero: true,
                    grid: { display: !horizontal, color: '#f1f5f9', drawBorder: false },
                    border: { display: false },
                    ticks: {
                        font: { family: FONT, size: 10 },
                        color: '#94a3b8',
                        precision: 0,
                        callback: tickCallback(horizontal ? spec.format : (spec.axisFormat || spec.format))
                    },
                    title: {
                        display: false,
                        text: spec.axisTitle || ''
                    }
                }
            };

            if (horizontal) {
                options.scales.y.ticks.callback = function (value) {
                    var label = this.getLabelForValue(value);
                    return label && label.length > 22 ? label.slice(0, 21) + '…' : label;
                };
            }
        }

        if (spec.cutout !== undefined) options.cutout = spec.cutout;
        if (spec.rotation !== undefined) options.rotation = spec.rotation;

        return options;
    }

    function mergeOptions(base, extra) {
        if (!extra) return base;
        Object.keys(extra).forEach(function (key) {
            if (extra[key] && typeof extra[key] === 'object' && !Array.isArray(extra[key])) {
                base[key] = mergeOptions(base[key] || {}, extra[key]);
            } else {
                base[key] = extra[key];
            }
        });
        return base;
    }

    function render(canvasId, spec) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        if (typeof global.Chart === 'undefined') {
            showFallback(canvas);
            return null;
        }

        var labels = spec.labels || [];
        var datasets = (spec.datasets || []).map(function (dataset, index) {
            return applyPalette(Object.assign({}, dataset), index, (spec.datasets || []).length, spec);
        });

        var config = {
            type: spec.type || 'bar',
            data: { labels: labels, datasets: datasets },
            options: mergeOptions(baseOptions(spec), spec.options)
        };

        canvas.dataset.rendered = '1';
        return new global.Chart(canvas.getContext('2d'), config);
    }

    function showFallback(canvas) {
        var frame = canvas.closest('[data-chart-frame]');
        if (!frame) return;
        var notice = frame.querySelector('[data-chart-fallback]');
        if (!notice) {
            notice = document.createElement('p');
            notice.setAttribute('data-chart-fallback', '');
            notice.className = 'text-[11px] text-slate-400 text-center py-10';
            notice.textContent = 'برای نمایش نمودار، کتابخانه Chart.js بارگذاری نشده است.';
            frame.appendChild(notice);
        }
    }

    function boot(callback) {
        function run() {
            if (typeof global.Chart === 'undefined') {
                document.querySelectorAll('[data-chart-frame] canvas').forEach(showFallback);
                return;
            }
            callback();
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', run);
        } else {
            run();
        }
    }

    global.ZitroCharts = {
        boot: boot,
        render: render,
        num: num,
        money: money,
        compact: compact,
        formatValue: formatValue,
        palette: palette,
        withAlpha: withAlpha
    };
})(window);
