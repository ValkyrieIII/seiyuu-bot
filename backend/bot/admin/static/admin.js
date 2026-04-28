/* ============================================================
   QQBot Admin — JavaScript
   ============================================================ */
(function () {
    "use strict";

    /* ========================================================
       Config
       ======================================================== */
    const API_BASE = "/admin/api";
    const REFRESH_INTERVAL = 30_000; // 概览页自动刷新间隔

    // 注册所有标签页：新增标签页只需在这里加一行
    const TABS = [
        { id: "overview", label: "概览", icon: "▣", init: initOverview, refresh: loadOverview },
        { id: "actors",   label: "声优管理", icon: "▷", init: initActors,   refresh: loadActors },
        { id: "images",  label: "图片管理", icon: "▥", init: initImages,  refresh: loadImages },
        { id: "aliases",  label: "别名管理", icon: "◉", init: initAliases,  refresh: loadAliases },
        { id: "sync",     label: "图片同步", icon: "↻", init: initSync,     refresh: null },
    ];

    /* ========================================================
       State
       ======================================================== */
    let currentTab = null;
    let refreshTimer = null;
    let overviewActorData = []; // 缓存在概览页加载的声优数据供别名页使用

    /* ========================================================
       API
       ======================================================== */
    async function api(path, options) {
        options = options || {};
        var headers = { "Content-Type": "application/json" };
        if (options.headers) {
            Object.assign(headers, options.headers);
        }
        var res = await fetch(path, {
            headers: headers,
            method: options.method || "GET",
            body: options.body,
        });
        var body = await res.json();
        if (!res.ok || body.success === false) {
            throw new Error(body.detail || body.error || "请求失败");
        }
        return body.data;
    }

    function apiGet(p)  { return api(API_BASE + p); }
    function apiPost(p, d) { return api(API_BASE + p, { method: "POST", body: JSON.stringify(d) }); }
    function apiPatch(p, d) { return api(API_BASE + p, { method: "PATCH", body: JSON.stringify(d) }); }
    function apiDelete(p) { return api(API_BASE + p, { method: "DELETE" }); }

    /* ========================================================
       UI — Toast
       ======================================================== */
    function showToast(msg, type) {
        type = type || "info";
        var container = document.getElementById("toastContainer");

        // Dismiss previous toasts of the same type to avoid pile-up
        var existing = container.querySelectorAll(".toast-" + type);
        existing.forEach(function (el) {
            el.classList.add("removing");
            el.addEventListener("animationend", function () { el.remove(); });
        });

        var el = document.createElement("div");
        el.className = "toast toast-" + type;
        var icons = { success: "✔", error: "✘", info: "ℹ", warning: "⚠" };
        el.innerHTML = "<span>" + (icons[type] || "") + "</span><span>" + escHtml(msg) + "</span>";
        container.appendChild(el);

        setTimeout(function () {
            el.classList.add("removing");
            el.addEventListener("animationend", function () { el.remove(); });
        }, 3000);
    }

    /* ========================================================
       UI — Confirm Dialog
       ======================================================== */
    function showConfirm(msg) {
        return new Promise(function (resolve) {
            var overlay = document.createElement("div");
            overlay.className = "modal-overlay";
            overlay.innerHTML =
                '<div class="modal-box">' +
                "<h3>确认操作</h3>" +
                "<p>" + escHtml(msg) + "</p>" +
                '<div class="modal-actions">' +
                '<button class="secondary small cancel-btn">取消</button>' +
                '<button class="danger small confirm-btn">确认</button>' +
                "</div></div>";
            document.body.appendChild(overlay);

            overlay.querySelector(".cancel-btn").addEventListener("click", function () { close(false); });
            overlay.querySelector(".confirm-btn").addEventListener("click", function () { close(true); });
            overlay.addEventListener("click", function (e) {
                if (e.target === overlay) close(false);
            });

            function close(result) {
                overlay.remove();
                resolve(result);
            }
        });
    }

    /* ========================================================
       UI — Loading helper
       ======================================================== */
    function withLoading(btn, promise) {
        var orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = "处理中...";
        return promise
            .then(function (r) {
                btn.disabled = false;
                btn.textContent = orig;
                return r;
            })
            .catch(function (e) {
                btn.disabled = false;
                btn.textContent = orig;
                throw e;
            });
    }

    /* ========================================================
       UI — Skeleton helpers
       ======================================================== */
    function showSkeleton(container, type) {
        container = typeof container === "string" ? document.getElementById(container) : container;
        // Release focus from elements about to be removed
        if (document.activeElement && container.contains(document.activeElement)) {
            document.activeElement.blur();
        }
        var scrollY = window.pageYOffset;
        if (type === "table") {
            var html = '<div class="table-wrap"><table><tbody>';
            for (var i = 0; i < 5; i++) {
                html += '<tr><td colspan="5"><div class="skeleton" style="height:18px;width:' +
                    ["60%", "80%", "50%", "70%", "45%"][i] + '"></div></td></tr>';
            }
            html += "</tbody></table></div>";
            container.innerHTML = html;
        } else if (type === "metrics") {
            container.innerHTML =
                '<div class="skeleton-metrics">' +
                Array(5).fill('<div class="skeleton skeleton-metric"></div>').join("") +
                "</div>";
        }
        window.scrollTo(0, scrollY);
    }

    /* ========================================================
       UI — Empty state
       ======================================================== */
    function showEmpty(container, msg) {
        container = typeof container === "string" ? document.getElementById(container) : container;
        if (document.activeElement && container.contains(document.activeElement)) {
            document.activeElement.blur();
        }
        var scrollY = window.pageYOffset;
        container.innerHTML =
            '<div class="empty-state">' +
            '<div class="empty-icon">∅</div>' +
            "<p>" + escHtml(msg || "暂无数据") + "</p>" +
            "</div>";
        window.scrollTo(0, scrollY);
    }

    /* ========================================================
       UI — Render Table
       ======================================================== */
    function renderTable(container, columns, rows, rowFn) {
        container = typeof container === "string" ? document.getElementById(container) : container;
        if (!rows || rows.length === 0) {
            showEmpty(container, "暂无数据");
            return;
        }
        var scrollY = window.pageYOffset;
        var html = '<div class="table-wrap"><table><thead><tr>';
        columns.forEach(function (col) {
            html += "<th>" + escHtml(col) + "</th>";
        });
        html += "</tr></thead><tbody>";
        rows.forEach(function (row) {
            html += rowFn(row);
        });
        html += "</tbody></table></div>";
        container.innerHTML = html;
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                window.scrollTo(0, scrollY);
            });
        });
    }

    /* ========================================================
       UI — Copy to clipboard
       ======================================================== */
    function copyId(text, event) {
        navigator.clipboard.writeText(String(text)).then(function () {
            var tip = document.createElement("div");
            tip.className = "copied-tip";
            tip.textContent = "已复制";
            tip.style.left = event.clientX + "px";
            tip.style.top = (event.clientY - 30) + "px";
            document.body.appendChild(tip);
            setTimeout(function () { tip.remove(); }, 1200);
        }).catch(function () {
            showToast("复制失败", "error");
        });
    }

    /* ========================================================
       UI — Badge
       ======================================================== */
    function badge(val, labels) {
        labels = labels || ["是", "否"];
        var cls = val ? "badge-on" : "badge-off";
        var txt = val ? labels[0] : labels[1];
        return '<span class="badge ' + cls + '">' + txt + "</span>";
    }

    /* ========================================================
       UI — Sanitize
       ======================================================== */
    var escMap = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    function escHtml(s) {
        return String(s).replace(/[&<>"']/g, function (ch) { return escMap[ch]; });
    }

    /* ========================================================
       Router
       ======================================================== */
    function getHash() {
        var h = location.hash.replace("#", "");
        if (!TABS.some(function (t) { return t.id === h; })) {
            h = TABS[0].id;
        }
        return h;
    }

    function switchTab(tabId) {
        if (currentTab === tabId) return;

        // Update sidebar nav
        document.querySelectorAll(".nav-item").forEach(function (el) {
            el.classList.toggle("active", el.dataset.tab === tabId);
        });

        // Update glass header
        var activeNav = document.querySelector('.nav-item[data-tab="' + tabId + '"]');
        if (activeNav) {
            document.getElementById("tabTitle").textContent = activeNav.dataset.title || tabId;
            document.getElementById("tabDesc").textContent = activeNav.dataset.desc || "";
        }

        // Update tab panels
        document.querySelectorAll(".tab-panel").forEach(function (el) {
            el.classList.toggle("active", el.id === "tab-" + tabId);
        });

        // Init tab if first visit
        var tab = TABS.find(function (t) { return t.id === tabId; });
        if (tab && tab.init) {
            tab.init();
            tab.init = null; // only init once, use refresh after
        }

        currentTab = tabId;

        // Manage auto-refresh
        clearInterval(refreshTimer);
        refreshTimer = null;
        stopSysInfoPoll();
        if (tabId === "overview") {
            startAutoRefresh();
            startSysInfoPoll();
        }
    }

    function startAutoRefresh() {
        clearInterval(refreshTimer);
        refreshTimer = setInterval(function () {
            if (document.hidden) return; // skip when page hidden
            var tab = TABS.find(function (t) { return t.id === "overview"; });
            if (tab && tab.refresh) tab.refresh();
        }, REFRESH_INTERVAL);
    }

    // Hash change listener
    window.addEventListener("hashchange", function () {
        switchTab(getHash());
    });

    // Sidebar nav click delegation
    document.addEventListener("click", function (e) {
        var navItem = e.target.closest(".nav-item");
        if (!navItem) return;
        e.preventDefault();
        var tabId = navItem.dataset.tab;
        if (tabId) {
            location.hash = "#" + tabId;
        }
    });

    /* ========================================================
       Tab: Overview
       ======================================================== */
    function initOverview() {
        loadOverview();
        bindOverviewActions();
        startSysInfoPoll();
    }

    function bindOverviewActions() {
        var refreshBtn = document.getElementById("refreshOverview");
        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                withLoading(refreshBtn, loadOverview()).catch(function (e) {
                    showToast(e.message, "error");
                });
            });
        }
    }

    async function loadOverview() {
        var metricsEl = document.getElementById("overviewMetrics");
        var logsEl = document.getElementById("overviewLogs");
        showSkeleton(metricsEl, "metrics");
        showSkeleton(logsEl, "table");

        var data;
        try { data = await apiGet("/overview"); } catch (e) {
            metricsEl.innerHTML = '<div class="empty-state"><span class="empty-icon">!</span><p>加载失败: ' + escHtml(e.message) + '</p></div>';
            logsEl.innerHTML = ""; return;
        }

        // Compact stat cards (5-column)
        var statItems = [
            ["声优总数", data.voice_actor_total, "accent"],
            ["图片总数", data.image_total, "gold"],
            ["别名总数", data.alias_total, ""],
            ["24h 请求", data.request_24h, ""],
            ["24h 成功率", data.success_rate_24h + "%", data.success_rate_24h >= 90 ? "green" : "accent"],
        ];
        metricsEl.innerHTML = "";
        statItems.forEach(function (item) {
            var div = document.createElement("div");
            div.className = "stat-card";
            div.innerHTML = '<div class="stat-label">' + escHtml(item[0]) + '</div>' +
                '<div class="stat-value ' + (item[2] || "") + '">' + escHtml(String(item[1])) + '</div>';
            metricsEl.appendChild(div);
        });

        // Recent logs with status badges
        renderTable(
            logsEl,
            ["时间", "用户", "状态", "耗时"],
            data.recent_logs,
            function (log) {
                var statusLabel = log.status || "-";
                var statusCls = "";
                if (statusLabel === "success") statusCls = "success";
                else if (statusLabel === "error") statusCls = "error";
                else if (statusLabel === "notfound") statusCls = "notfound";
                return (
                    "<tr>" +
                    "<td>" + escHtml((log.created_at || "").replace("T", " ").slice(0, 19)) + "</td>" +
                    "<td>" + escHtml(String(log.user_id || "-")) + "</td>" +
                    '<td><span class="status-badge ' + statusCls + '">' + escHtml(statusLabel) + "</span></td>" +
                    "<td>" + escHtml(String(log.response_time_ms || "-")) + " ms</td>" +
                    "</tr>"
                );
            }
        );
    }

    /* ========================================================
       Tab: Voice Actors
       ======================================================== */
    function initActors() {
        loadActors();
        bindActorActions();
        bindActorTableEvents();
    }

    function bindActorActions() {
        var addBtn = document.getElementById("addActor");
        if (addBtn) {
            addBtn.addEventListener("click", function () {
                var nameEl = document.getElementById("actorName");
                var descEl = document.getElementById("actorDesc");
                var name = nameEl.value.trim();
                if (!name) {
                    nameEl.classList.add("error");
                    showToast("请输入声优名称", "warning");
                    setTimeout(function () { nameEl.classList.remove("error"); }, 600);
                    return;
                }
                withLoading(addBtn, apiPost("/voice-actors", { name: name, description: descEl.value.trim() }))
                    .then(function () {
                        nameEl.value = "";
                        descEl.value = "";
                        showToast("新增声优成功", "success");
                        return Promise.all([loadActors(), loadOverview()]);
                    })
                    .catch(function (e) { showToast(e.message, "error"); });
            });
        }

        // Actor name input: clear error on type
        var nameEl = document.getElementById("actorName");
        if (nameEl) {
            nameEl.addEventListener("input", function () { nameEl.classList.remove("error"); });
        }
    }

    async function loadActors() {
        var scrollY = window.pageYOffset;
        var container = document.getElementById("actorTable");
        var aliasTarget = document.getElementById("aliasTarget");
        showSkeleton(container, "table");

        var actors;
        try {
            actors = await apiGet("/voice-actors");
        } catch (e) {
            showEmpty(container, "加载失败: " + e.message);
            return;
        }

        overviewActorData = actors;

        // Voice actors table
        renderTable(
            container,
            ["ID", "名称", "图片数", "状态", "启用"],
            actors,
            function (actor) {
                return (
                    "<tr>" +
                    '<td class="id-col" data-copy="' + actor.id + '">' + actor.id + "</td>" +
                    '<td class="name-col">' + escHtml(actor.name) + "</td>" +
                    "<td>" + actor.image_count + "</td>" +
                    "<td>" + badge(actor.is_active) + "</td>" +
                    "<td>" +
                    '<label class="toggle-switch">' +
                    '<input type="checkbox" class="toggleActor" data-id="' + actor.id +
                    '" ' + (actor.is_active ? "checked" : "") + ">" +
                    '<span class="toggle-slider"></span>' +
                    "</label>" +
                    "</td></tr>"
                );
            }
        );

        // Populate alias target dropdown
        if (aliasTarget) {
            var currentVal = aliasTarget.value;
            aliasTarget.innerHTML = "";
            actors.forEach(function (actor) {
                var opt = document.createElement("option");
                opt.value = actor.id;
                opt.textContent = actor.name + " (#" + actor.id + ")";
                aliasTarget.appendChild(opt);
            });
            if (currentVal) aliasTarget.value = currentVal;
        }

        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                window.scrollTo(0, scrollY);
            });
        });
    }

    function bindActorTableEvents() {
        var container = document.getElementById("actorTable");
        if (!container || container._eventsBound) return;
        container._eventsBound = true;

        container.addEventListener("change", function (e) {
            var toggle = e.target.closest(".toggleActor");
            if (toggle) {
                var id = Number(toggle.dataset.id);
                var checked = toggle.checked;
                var checkbox = toggle;
                checkbox.disabled = true;
                apiPatch("/voice-actors/" + id, { is_active: checked })
                    .then(function () {
                        showToast("声优状态已更新", "success");
                        return Promise.all([loadActors(), loadOverview()]);
                    })
                    .catch(function (e) {
                        checkbox.checked = !checked;
                        checkbox.disabled = false;
                        showToast(e.message, "error");
                    });
            }
        });
        container.addEventListener("click", function (e) {
            var copyEl = e.target.closest("[data-copy]");
            if (copyEl) {
                copyId(copyEl.dataset.copy, e);
            }
        });
    }

    /* ========================================================
       Tab: Aliases
       ======================================================== */
    function initAliases() {
        // Ensure actor dropdown is populated
        if (overviewActorData.length === 0) {
            apiGet("/voice-actors").then(function (actors) {
                overviewActorData = actors;
                populateAliasTarget();
            }).catch(function () {});
        } else {
            populateAliasTarget();
        }
        loadAliases();
        bindAliasActions();
        bindAliasTableEvents();
    }

    function populateAliasTarget() {
        var target = document.getElementById("aliasTarget");
        if (!target) return;
        var val = target.value;
        target.innerHTML = "";
        overviewActorData.forEach(function (actor) {
            var opt = document.createElement("option");
            opt.value = actor.id;
            opt.textContent = actor.name + " (#" + actor.id + ")";
            target.appendChild(opt);
        });
        if (val) target.value = val;
    }

    function bindAliasActions() {
        var addBtn = document.getElementById("addAlias");
        if (addBtn) {
            addBtn.addEventListener("click", function () {
                var nameEl = document.getElementById("aliasName");
                var aliasName = nameEl.value.trim();
                var targetId = Number(document.getElementById("aliasTarget").value);
                var priority = Number(document.getElementById("aliasPriority").value || 0);

                if (!aliasName || !targetId) {
                    if (!aliasName) {
                        nameEl.classList.add("error");
                        setTimeout(function () { nameEl.classList.remove("error"); }, 600);
                    }
                    showToast("请填写别名并选择目标声优", "warning");
                    return;
                }
                withLoading(addBtn,
                    apiPost("/aliases", { alias_name: aliasName, target_voice_actor_id: targetId, priority: priority })
                )
                    .then(function () {
                        nameEl.value = "";
                        showToast("新增别名成功", "success");
                        return Promise.all([loadAliases(), loadOverview()]);
                    })
                    .catch(function (e) { showToast(e.message, "error"); });
            });
        }

        var nameEl = document.getElementById("aliasName");
        if (nameEl) {
            nameEl.addEventListener("input", function () { nameEl.classList.remove("error"); });
        }
    }

    async function loadAliases() {
        var container = document.getElementById("aliasTable");
        showSkeleton(container, "table");

        var aliases;
        try {
            aliases = await apiGet("/aliases");
        } catch (e) {
            showEmpty(container, "加载失败: " + e.message);
            return;
        }

        renderTable(
            container,
            ["ID", "别名", "目标声优", "优先级", "操作"],
            aliases,
            function (item) {
                return (
                    "<tr>" +
                    '<td class="id-col" data-copy="' + item.id + '">' + item.id + "</td>" +
                    "<td>" + escHtml(item.alias_name) + "</td>" +
                    "<td>" + escHtml(item.target_voice_actor_name) + "</td>" +
                    "<td>" + item.priority + "</td>" +
                    "<td>" +
                    '<button class="small danger deleteAlias" data-id="' + item.id +
                    '" data-name="' + escHtml(item.alias_name) + '">删除</button>' +
                    "</td></tr>"
                );
            }
        );

    }

    function bindAliasTableEvents() {
        var container = document.getElementById("aliasTable");
        if (!container || container._eventsBound) return;
        container._eventsBound = true;

        container.addEventListener("click", function (e) {
            var delBtn = e.target.closest(".deleteAlias");
            if (delBtn) {
                var id = Number(delBtn.dataset.id);
                var name = delBtn.dataset.name;
                showConfirm("确定删除别名「" + name + "」吗？此操作不可撤销。")
                    .then(function (ok) {
                        if (!ok) return;
                        return apiDelete("/aliases/" + id).then(function () {
                            showToast("别名已删除", "success");
                            return Promise.all([loadAliases(), loadOverview()]);
                        });
                    })
                    .catch(function (e) { showToast(e.message, "error"); });
            }
            var copyEl = e.target.closest("[data-copy]");
            if (copyEl) {
                copyId(copyEl.dataset.copy, e);
            }
        });
    }

    /* ========================================================
       Tab: Image Sync
       ======================================================== */
    function initSync() {
        var btn = document.getElementById("syncBtn");
        if (!btn) return;

        btn.addEventListener("click", function () {
            var resultEl = document.getElementById("syncResult");
            resultEl.innerHTML =
                '<div class="empty-state"><p>正在执行同步中...</p></div>';

            withLoading(btn, apiPost("/sync-images", {}))
                .then(function (data) {
                    var items = [
                        ["新增声优", data.added_actors, "positive"],
                        ["禁用声优", data.disabled_actors, "neutral"],
                        ["新增图片", data.added_images, "positive"],
                        ["更新图片", data.updated_images, "neutral"],
                        ["禁用图片", data.disabled_images, "neutral"],
                    ];
                    var html = '<div class="sync-results">';
                    items.forEach(function (item) {
                        html +=
                            '<div class="sync-result">' +
                            '<div class="num ' + item[2] + '">' + item[1] + "</div>" +
                            '<div class="lbl">' + item[0] + "</div>" +
                            "</div>";
                    });
                    html += "</div>";
                    resultEl.innerHTML = html;
                    showToast("图片同步完成", "success");
                    return Promise.all([loadOverview(), loadActors()]);
                })
                .catch(function (e) {
                    document.getElementById("syncResult").innerHTML =
                        '<div class="empty-state"><p>同步失败: ' + escHtml(e.message) + "</p></div>";
                    showToast(e.message, "error");
                });
        });
    }

    /* ========================================================
       Tab: Image Management
       ======================================================== */
    var imagePage = 1;
    var imagePageSize = 20;

    function initImages() {
        populateImageActorDropdowns();
        loadImages(1);
        bindImageActions();
        bindImageFilterEvents();
        bindImageTableEvents();
    }

    function populateImageActorDropdowns() {
        var fetchActors;
        if (overviewActorData.length > 0) {
            fetchActors = Promise.resolve(overviewActorData);
        } else {
            fetchActors = apiGet("/voice-actors").then(function (actors) {
                overviewActorData = actors;
                return actors;
            });
        }
        fetchActors.then(function (actors) {
            var uploadSel = document.getElementById("imgUploadActor");
            var filterSel = document.getElementById("imgFilterActor");
            [uploadSel, filterSel].forEach(function (sel) {
                if (!sel) return;
                var val = sel.value;
                sel.innerHTML = "";
                if (sel === filterSel) {
                    var optAll = document.createElement("option");
                    optAll.value = "";
                    optAll.textContent = "全部声优";
                    sel.appendChild(optAll);
                }
                actors.forEach(function (actor) {
                    var opt = document.createElement("option");
                    opt.value = actor.id;
                    opt.textContent = actor.name + " (#" + actor.id + ")";
                    sel.appendChild(opt);
                });
                if (val) sel.value = val;
            });
        }).catch(function () {});
    }

    function bindImageActions() {
        var uploadBtn = document.getElementById("uploadImgBtn");
        if (uploadBtn) {
            uploadBtn.addEventListener("click", function () {
                var fileInput = document.getElementById("imgFileInput");
                var actorSelect = document.getElementById("imgUploadActor");
                var file = fileInput.files[0];
                var actorId = actorSelect.value;

                if (!file) {
                    showToast("请选择图片文件", "warning");
                    return;
                }
                if (!actorId) {
                    showToast("请选择目标声优", "warning");
                    return;
                }

                var formData = new FormData();
                formData.append("file", file);

                withLoading(uploadBtn,
                    fetch(API_BASE + "/images/upload?voice_actor_id=" + encodeURIComponent(actorId), {
                        method: "POST",
                        body: formData,
                    }).then(function (res) { return res.json(); })
                    .then(function (body) {
                        if (!body.success) throw new Error(body.detail || "上传失败");
                        fileInput.value = "";
                        showToast("上传成功", "success");
                        return loadImages(imagePage);
                    })
                ).catch(function (e) {
                    showToast(e.message, "error");
                });
            });
        }
    }

    function bindImageFilterEvents() {
        var filterActor = document.getElementById("imgFilterActor");
        var searchInput = document.getElementById("imgSearch");

        var doFilter = function () {
            imagePage = 1;
            loadImages(1);
        };

        if (filterActor) {
            filterActor.addEventListener("change", doFilter);
        }
        if (searchInput) {
            var debounceTimer;
            searchInput.addEventListener("input", function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(doFilter, 300);
            });
        }
    }

    function loadImages(page) {
        page = page || 1;
        imagePage = page;

        var scrollY = window.pageYOffset;
        var container = document.getElementById("imageTable");
        var paginationEl = document.getElementById("imagePagination");
        showSkeleton(container, "table");
        paginationEl.innerHTML = "";

        var params = "?page=" + page + "&page_size=" + imagePageSize;
        var filterActor = document.getElementById("imgFilterActor");
        if (filterActor && filterActor.value) {
            params += "&voice_actor_id=" + encodeURIComponent(filterActor.value);
        }
        var searchInput = document.getElementById("imgSearch");
        if (searchInput && searchInput.value.trim()) {
            params += "&search=" + encodeURIComponent(searchInput.value.trim());
        }

        apiGet("/images" + params)
            .then(function (data) {
                renderTable(
                    container,
                    ["预览", "文件名", "所属声优", "大小(KB)", "启用", "操作"],
                    data.items,
                    function (img) {
                        return (
                            "<tr>" +
                            '<td><img src="' + API_BASE + '/images/' + img.id + '/file" ' +
                            'class="img-thumb" loading="lazy" /></td>' +
                            '<td class="name-col">' + escHtml(img.filename) + "</td>" +
                            "<td>" + escHtml(img.voice_actor_name) + "</td>" +
                            "<td>" + img.size_kb + "</td>" +
                            "<td>" +
                            '<label class="toggle-switch">' +
                            '<input type="checkbox" class="toggleImage" data-id="' + img.id +
                            '" ' + (img.is_active ? "checked" : "") + ">" +
                            '<span class="toggle-slider"></span>' +
                            "</label>" +
                            "</td>" +
                            "<td>" +
                            '<button class="small danger deleteImage" data-id="' + img.id +
                            '" data-name="' + escHtml(img.filename) + '">删除</button>' +
                            "</td></tr>"
                        );
                    }
                );

                // Pagination
                var totalPages = Math.ceil(data.total / data.page_size) || 1;
                if (totalPages > 1) {
                    var pageHtml = "";
                    pageHtml +=
                        '<button class="small secondary" ' + (page <= 1 ? "disabled" : "") +
                        ' id="imgPrevPage">上一页</button> ';
                    pageHtml +=
                        '<span style="margin:0 10px;font-size:13px">' + page + " / " + totalPages + "</span> ";
                    pageHtml +=
                        '<button class="small secondary" ' + (page >= totalPages ? "disabled" : "") +
                        ' id="imgNextPage">下一页</button>';
                    paginationEl.innerHTML = pageHtml;

                    var prevBtn = document.getElementById("imgPrevPage");
                    var nextBtn = document.getElementById("imgNextPage");
                    if (prevBtn) {
                        prevBtn.addEventListener("click", function () { loadImages(page - 1); });
                    }
                    if (nextBtn) {
                        nextBtn.addEventListener("click", function () { loadImages(page + 1); });
                    }
                }
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        window.scrollTo(0, scrollY);
                    });
                });
            })
            .catch(function (e) {
                showEmpty(container, "加载失败: " + e.message);
            });
    }

    function bindImageTableEvents() {
        var container = document.getElementById("imageTable");
        if (!container || container._eventsBound) return;
        container._eventsBound = true;

        container.addEventListener("change", function (e) {
            var toggleCb = e.target.closest(".toggleImage");
            if (toggleCb) {
                var id = Number(toggleCb.dataset.id);
                var checked = toggleCb.checked;
                toggleCb.disabled = true;
                apiPatch("/images/" + id, { is_active: checked })
                    .then(function () {
                        showToast("图片状态已更新", "success");
                        loadImages(imagePage);
                    })
                    .catch(function (e) {
                        toggleCb.checked = !checked;
                        toggleCb.disabled = false;
                        showToast(e.message, "error");
                    });
            }
        });
        container.addEventListener("click", function (e) {
            var delBtn = e.target.closest(".deleteImage");
            if (delBtn) {
                var id = Number(delBtn.dataset.id);
                var name = delBtn.dataset.name;
                showConfirm("确定删除图片「" + name + "」吗？此操作会同时删除文件，不可撤销。")
                    .then(function (ok) {
                        if (!ok) return;
                        return apiDelete("/images/" + id).then(function () {
                            showToast("图片已删除", "success");
                            return loadImages(imagePage);
                        });
                    })
                    .catch(function (e) { showToast(e.message, "error"); });
            }
        });
    }

    /* ========================================================
       System Gauge — CPU / Memory dashboard
       ======================================================== */
    var sysInfoTimer = null;
    var CIRC = 2 * Math.PI * 32; // circumference for r=32

    function loadSystemInfo() {
        apiGet("/system-info")
            .then(function (data) {
                var gaugeHtml =
                    '<div class="gauge-cards">' +
                    '<div class="card gauge-card">' +
                    '<div class="gauge-block-label">CPU</div>' +
                    '<div class="gauge">' +
                    buildGauge(data.cpu_percent, 100, data.cpu_percent + "%", "占用", "var(--brand)") +
                    "</div>" +
                    '<div class="gauge-cpu-info">' + escHtml(data.cpu_model) + "</div>" +
                    "</div>" +
                    '<div class="card gauge-card">' +
                    '<div class="gauge-block-label">MEM</div>' +
                    '<div class="gauge">' +
                    buildGauge(
                        data.memory_mb, data.memory_total_mb,
                        data.memory_mb + " MB", data.memory_total_mb + " MB",
                        "var(--brand-2)"
                    ) +
                    "</div></div>" +
                    "</div>";
                document.getElementById("systemGauges").innerHTML = gaugeHtml;
                animateGauges();
            })
            .catch(function () {
                document.getElementById("systemGauges").innerHTML =
                    '<span class="empty-state" style="padding:20px"><p>系统信息获取失败</p></span>';
            });
    }

    function buildGauge(value, max, line1, line2, color) {
        var pct = Math.min(value / Math.max(max, 1), 1);
        var offset = CIRC * (1 - pct);
        return (
            '<svg width="80" height="80" viewBox="0 0 80 80" class="gauge-ring">' +
            '<circle class="gauge-ring-bg" cx="40" cy="40" r="32" />' +
            '<circle class="gauge-ring-fg" cx="40" cy="40" r="32" ' +
            'stroke="' + color + '" ' +
            'stroke-dasharray="' + CIRC + '" ' +
            'stroke-dashoffset="' + CIRC + '" ' +
            'data-target="' + offset + '" />' +
            "</svg>" +
            '<div class="gauge-info">' +
            '<span class="gauge-value">' + escHtml(line1) + "</span>" +
            '<span class="gauge-sub">' + escHtml(line2) + "</span>" +
            "</div>"
        );
    }

    function animateGauges() {
        // Use rAF to ensure DOM is ready, then set target offsets
        requestAnimationFrame(function () {
            document.querySelectorAll(".gauge-ring-fg[data-target]").forEach(function (ring) {
                ring.style.strokeDashoffset = ring.dataset.target;
            });
        });
    }

    function startSysInfoPoll() {
        loadSystemInfo();
        clearInterval(sysInfoTimer);
        sysInfoTimer = setInterval(function () {
            if (document.hidden) return;
            loadSystemInfo();
        }, 1000);
    }

    function stopSysInfoPoll() {
        clearInterval(sysInfoTimer);
        sysInfoTimer = null;
    }

    /* ========================================================
       Search / Filter — actor & alias tables
       ======================================================== */
    function bindSearch() {
        var searchActor = document.getElementById("searchActor");
        if (searchActor) {
            searchActor.addEventListener("input", function () {
                filterTable("actorTable", searchActor.value);
            });
        }

        var searchAlias = document.getElementById("searchAlias");
        if (searchAlias) {
            searchAlias.addEventListener("input", function () {
                filterTable("aliasTable", searchAlias.value);
            });
        }
    }

    function filterTable(containerId, query) {
        var container = document.getElementById(containerId);
        var tableWrap = container.querySelector(".table-wrap");
        if (!tableWrap) return;
        var rows = tableWrap.querySelectorAll("tbody tr");
        var q = query.toLowerCase().trim();
        var visible = 0;
        rows.forEach(function (tr) {
            var match = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
            tr.style.display = match ? "" : "none";
            if (match) visible++;
        });
        // Show empty if no match
        var existing = container.querySelector(".empty-state");
        if (visible === 0 && q) {
            if (!existing) {
                var div = document.createElement("div");
                div.className = "empty-state";
                div.innerHTML = "<p>无匹配结果</p>";
                container.appendChild(div);
            }
            tableWrap.style.display = "none";
        } else {
            if (existing) existing.remove();
            tableWrap.style.display = "";
        }
    }

    /* ========================================================
       Init — Bootstrap
       ======================================================== */
    function bootstrap() {
        bindSearch();
        var initialTab = getHash();
        // Set initial hash if none
        if (!location.hash || location.hash === "#") {
            history.replaceState(null, "", "#" + initialTab);
        }
        switchTab(initialTab);
        showToast("后台就绪", "success");
    }

    // Page visibility: pause/resume auto-refresh
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden && currentTab === "overview") {
            var tab = TABS.find(function (t) { return t.id === "overview"; });
            if (tab && tab.refresh) tab.refresh();
            startAutoRefresh();
            startSysInfoPoll();
        } else if (document.hidden) {
            clearInterval(refreshTimer);
            refreshTimer = null;
            stopSysInfoPoll();
        }
    });

    // Go!
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bootstrap);
    } else {
        bootstrap();
    }
})();
