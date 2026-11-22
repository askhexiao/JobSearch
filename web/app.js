/* UniFit100 订阅页交互逻辑（零依赖，原生 JS） */
(function () {
  "use strict";

  var MAX_TITLES = 5;
  var MAX_LOCATIONS = 5;
  var UNLIMITED = "不限";

  var titleList = document.getElementById("title-list");
  var locationList = document.getElementById("location-list");
  var addTitle = document.getElementById("add-title");
  var addLocation = document.getElementById("add-location");
  var form = document.getElementById("subscribe-form");
  var submitBtn = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");

  // ---------- 动态字段 ----------
  function makeTitleRow(value) {
    var row = document.createElement("div");
    row.className = "row";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "如：产品经理 / 数据分析 / Java 开发";
    input.value = value || "";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "remove-btn";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "删除");
    btn.addEventListener("click", function () {
      if (titleCount() <= 1) return; // 至少保留 1 个
      row.remove();
      refreshButtons();
    });
    row.appendChild(input);
    row.appendChild(btn);
    return row;
  }

  function makeLocationRow(value, withUnlimited) {
    var row = document.createElement("div");
    row.className = "row";
    var sel = document.createElement("select");
    if (withUnlimited) {
      var opt = document.createElement("option");
      opt.value = UNLIMITED;
      opt.textContent = UNLIMITED;
      sel.appendChild(opt);
    } else {
      var placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "请选择城市";
      sel.appendChild(placeholder);
    }
    populateLocationOptions(sel, value);
    sel.addEventListener("change", syncLocationUI);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "remove-btn";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "删除");
    btn.addEventListener("click", function () {
      if (locationCount() <= 1) return; // 至少保留 1 个
      row.remove();
      syncLocationUI();
    });
    row.appendChild(sel);
    row.appendChild(btn);
    return row;
  }

  var locationChoices = [];
  function populateLocationOptions(sel, selected) {
    locationChoices.forEach(function (loc) {
      var opt = document.createElement("option");
      opt.value = loc;
      opt.textContent = loc;
      if (loc === selected) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function titleCount() { return titleList.querySelectorAll("input").length; }
  function locationCount() { return locationList.querySelectorAll("select").length; }

  function firstLocationIsUnlimited() {
    var first = locationList.querySelector("select");
    return first && first.value === UNLIMITED;
  }

  function syncLocationUI() {
    var unlimited = firstLocationIsUnlimited();
    addLocation.disabled = unlimited || locationCount() >= MAX_LOCATIONS;
    // 「不限」时，多余的地点行无意义，移除之。
    if (unlimited) {
      var sels = locationList.querySelectorAll("select");
      sels.forEach(function (sel, i) {
        if (i > 0 && sel.closest(".row")) sel.closest(".row").remove();
      });
    }
    refreshButtons();
  }

  function refreshButtons() {
    addTitle.disabled = titleCount() >= MAX_TITLES;
    addLocation.disabled = firstLocationIsUnlimited() || locationCount() >= MAX_LOCATIONS;
  }

  addTitle.addEventListener("click", function () {
    if (titleCount() < MAX_TITLES) { titleList.appendChild(makeTitleRow("")); refreshButtons(); }
  });
  addLocation.addEventListener("click", function () {
    if (locationCount() < MAX_LOCATIONS && !firstLocationIsUnlimited()) {
      locationList.appendChild(makeLocationRow("", false));
      syncLocationUI();
    }
  });

  // ---------- 地点候选 ----------
  fetch("/api/locations")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      locationChoices = data.locations || [];
      // 已渲染的地点下拉补全候选（首行「不限」已在初始化时带上）。
      locationList.querySelectorAll("select").forEach(function (sel) {
        if (!sel.querySelector("option[value='" + UNLIMITED + "']")) {
          populateLocationOptions(sel, "");
        }
      });
    })
    .catch(function () { /* 候选列表非必需 */ });

  // ---------- 表单提交 ----------
  function setStatus(msg, ok) {
    statusEl.textContent = msg;
    statusEl.className = "status " + (ok ? "ok" : "err");
  }

  function collectTitles() {
    var out = [];
    titleList.querySelectorAll("input").forEach(function (i) {
      var v = i.value.trim();
      if (v) out.push(v);
    });
    return out;
  }

  function collectLocations() {
    var out = [];
    locationList.querySelectorAll("select").forEach(function (s) {
      var v = s.value;
      if (v) out.push(v);
    });
    return out;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = document.getElementById("email").value.trim();
    var titles = collectTitles();
    var locations = collectLocations();
    var recruitType = document.getElementById("recruit-type").value;
    var employerDb = document.getElementById("employer-db").value;
    var frequency = document.getElementById("frequency").value;
    var publishWithin = document.getElementById("publish-within").value;

    if (!document.getElementById("consent").checked) {
      setStatus("请先同意隐私说明", false); return;
    }
    if (!email) { setStatus("请输入邮箱", false); return; }
    if (titles.length === 0 && locations.length === 0) {
      setStatus("请至少填写一个职位名称或工作地点", false); return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "提交中…";

    fetch("/api/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        titles: titles,
        locations: locations,
        recruit_type: recruitType,
        employer_db: employerDb,
        frequency: frequency,
        publish_within: publishWithin,
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          setStatus("✅ " + (res.data.message || "订阅成功！"), true);
          resetForm();
        } else {
          setStatus((res.data && res.data.error) || "提交失败，请稍后再试", false);
        }
      })
      .catch(function () { setStatus("网络错误，请稍后再试", false); })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "立即订阅";
      });
  });

  function resetForm() {
    form.reset();
    titleList.innerHTML = "";
    locationList.innerHTML = "";
    titleList.appendChild(makeTitleRow("设计师"));
    titleList.appendChild(makeTitleRow("产品经理"));
    locationList.appendChild(makeLocationRow(UNLIMITED, true));
    syncLocationUI();
  }

  // ---------- 初始化 ----------
  titleList.appendChild(makeTitleRow("设计师"));
  titleList.appendChild(makeTitleRow("产品经理"));
  locationList.appendChild(makeLocationRow(UNLIMITED, true));
  refreshButtons();
})();
