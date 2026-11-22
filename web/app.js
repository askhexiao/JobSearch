/* UniFit100 订阅页交互逻辑（零依赖，原生 JS） */
(function () {
  "use strict";

  var MAX_TITLES = 3;
  var MAX_LOCATIONS = 4;

  var titleList = document.getElementById("title-list");
  var locationList = document.getElementById("location-list");
  var addTitle = document.getElementById("add-title");
  var addLocation = document.getElementById("add-location");
  var unlimited = document.getElementById("unlimited");
  var locationBlock = document.getElementById("location-block");
  var form = document.getElementById("subscribe-form");
  var submitBtn = document.getElementById("submit-btn");
  var statusEl = document.getElementById("status");
  var datalist = document.getElementById("location-options");

  // ---------- 动态字段 ----------
  function makeTitleRow() {
    var row = document.createElement("div");
    row.className = "row";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "如：产品经理 / 数据分析 / Java 开发";
    input.setAttribute("list", "title-suggestions");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "remove-btn";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "删除");
    btn.addEventListener("click", function () { row.remove(); refreshButtons(); });
    row.appendChild(input);
    row.appendChild(btn);
    return row;
  }

  function makeLocationRow() {
    var row = document.createElement("div");
    row.className = "row";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "如：北京 / 上海 / 广东";
    input.setAttribute("list", "location-options");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "remove-btn";
    btn.textContent = "×";
    btn.setAttribute("aria-label", "删除");
    btn.addEventListener("click", function () { row.remove(); refreshButtons(); });
    row.appendChild(input);
    row.appendChild(btn);
    return row;
  }

  function titleCount() { return titleList.querySelectorAll("input").length; }
  function locationCount() { return locationList.querySelectorAll("input").length; }

  function refreshButtons() {
    addTitle.disabled = titleCount() >= MAX_TITLES;
    addLocation.disabled = locationCount() >= MAX_LOCATIONS;
    unlimited.disabled = locationCount() > 0;
  }

  addTitle.addEventListener("click", function () {
    if (titleCount() < MAX_TITLES) { titleList.appendChild(makeTitleRow()); refreshButtons(); }
  });
  addLocation.addEventListener("click", function () {
    if (locationCount() < MAX_LOCATIONS) { locationList.appendChild(makeLocationRow()); refreshButtons(); }
  });

  unlimited.addEventListener("change", function () {
    if (unlimited.checked) {
      locationList.innerHTML = "";
      locationBlock.classList.add("disabled");
    } else {
      locationBlock.classList.remove("disabled");
    }
    refreshButtons();
  });

  // ---------- 地点候选 ----------
  fetch("/api/locations")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      (data.locations || []).forEach(function (loc) {
        var opt = document.createElement("option");
        opt.value = loc;
        datalist.appendChild(opt);
      });
    })
    .catch(function () { /* 候选列表非必需 */ });

  // ---------- 表单提交 ----------
  function setStatus(msg, ok) {
    statusEl.textContent = msg;
    statusEl.className = "status " + (ok ? "ok" : "err");
  }

  function collect(listEl) {
    var out = [];
    listEl.querySelectorAll("input").forEach(function (i) {
      var v = i.value.trim();
      if (v) out.push(v);
    });
    return out;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = document.getElementById("email").value.trim();
    var titles = collect(titleList);
    var locations = collect(locationList);
    var isUnlimited = unlimited.checked;

    if (!document.getElementById("consent").checked) {
      setStatus("请先同意隐私说明", false); return;
    }
    if (!email) { setStatus("请输入邮箱", false); return; }
    if (titles.length === 0 && !isUnlimited && locations.length === 0) {
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
        location_unlimited: isUnlimited,
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          setStatus("✅ " + (res.data.message || "订阅成功！"), true);
          form.reset();
          titleList.innerHTML = "";
          locationList.innerHTML = "";
          unlimited.checked = false;
          locationBlock.classList.remove("disabled");
          titleList.appendChild(makeTitleRow());
          refreshButtons();
        } else {
          setStatus((res.data && res.data.error) || "提交失败，请稍后再试", false);
        }
      })
      .catch(function () {
        setStatus("网络错误，请稍后再试", false);
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "立即订阅";
      });
  });

  // ---------- 初始化 ----------
  titleList.appendChild(makeTitleRow());
  refreshButtons();
})();
