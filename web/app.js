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

  var pcaData = []; // 省-市-县数据

  function makeOption(value, text) {
    var o = document.createElement("option");
    o.value = value;
    o.textContent = text;
    return o;
  }

  // ---------- 职位名称（无删除） ----------
  function makeTitleRow(value) {
    var row = document.createElement("div");
    row.className = "row";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "如：产品经理 / 数据分析 / Java 开发";
    input.value = value || "";
    row.appendChild(input);
    return row;
  }

  function titleCount() { return titleList.querySelectorAll("input").length; }

  addTitle.addEventListener("click", function () {
    if (titleCount() < MAX_TITLES) {
      titleList.appendChild(makeTitleRow(""));
      refreshButtons();
    }
  });

  // ---------- 工作地点（省-市-县联动，无删除） ----------
  function makeLocationRow(initialProvince) {
    var row = document.createElement("div");
    row.className = "location-row";

    var prov = document.createElement("select");
    prov.className = "loc-province";
    var city = document.createElement("select");
    city.className = "loc-city";
    city.disabled = true;
    var county = document.createElement("select");
    county.className = "loc-county";
    county.disabled = true;

    // 省：新增行加「请选择省」，首行默认「不限」
    if (initialProvince !== UNLIMITED) {
      prov.appendChild(makeOption("", "请选择省"));
    }
    prov.appendChild(makeOption(UNLIMITED, UNLIMITED));
    pcaData.forEach(function (p) { prov.appendChild(makeOption(p.name, p.name)); });
    prov.value = initialProvince || "";

    city.appendChild(makeOption("", "请选择市"));
    county.appendChild(makeOption("", "请选择县区"));

    prov.addEventListener("change", function () { onProvinceChange(row); });
    city.addEventListener("change", function () { onCityChange(row); });

    row.appendChild(prov);
    row.appendChild(city);
    row.appendChild(county);
    return row;
  }

  function onProvinceChange(row) {
    var prov = row.querySelector(".loc-province");
    var city = row.querySelector(".loc-city");
    var county = row.querySelector(".loc-county");
    city.innerHTML = "";
    county.innerHTML = "";

    if (!prov.value || prov.value === UNLIMITED) {
      city.disabled = true;
      county.disabled = true;
      city.appendChild(makeOption("", "请选择市"));
      county.appendChild(makeOption("", "请选择县区"));
      syncLocationUI();
      return;
    }

    var p = pcaData.find(function (x) { return x.name === prov.value; });
    city.disabled = false;
    city.appendChild(makeOption("", "请选择市"));
    (p ? p.children : []).forEach(function (c) { city.appendChild(makeOption(c.name, c.name)); });
    county.disabled = true;
    county.appendChild(makeOption("", "请选择县区"));
    syncLocationUI();
  }

  function onCityChange(row) {
    var prov = row.querySelector(".loc-province");
    var city = row.querySelector(".loc-city");
    var county = row.querySelector(".loc-county");
    county.innerHTML = "";

    var p = pcaData.find(function (x) { return x.name === prov.value; });
    var c = p && p.children.find(function (y) { return y.name === city.value; });
    if (c && c.children && c.children.length) {
      county.disabled = false;
      county.appendChild(makeOption("", "请选择县区"));
      c.children.forEach(function (a) { county.appendChild(makeOption(a.name, a.name)); });
    } else {
      county.disabled = true;
      county.appendChild(makeOption("", "请选择县区"));
    }
  }

  function locationCount() { return locationList.querySelectorAll(".location-row").length; }

  function anyUnlimited() {
    var found = false;
    locationList.querySelectorAll(".loc-province").forEach(function (p) {
      if (p.value === UNLIMITED) found = true;
    });
    return found;
  }

  function syncLocationUI() {
    addLocation.disabled = anyUnlimited() || locationCount() >= MAX_LOCATIONS;
    refreshButtons();
  }

  function refreshButtons() {
    addTitle.disabled = titleCount() >= MAX_TITLES;
    addLocation.disabled = anyUnlimited() || locationCount() >= MAX_LOCATIONS;
  }

  addLocation.addEventListener("click", function () {
    if (locationCount() < MAX_LOCATIONS && !anyUnlimited()) {
      locationList.appendChild(makeLocationRow(""));
      syncLocationUI();
    }
  });

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
    locationList.querySelectorAll(".location-row").forEach(function (row) {
      var prov = row.querySelector(".loc-province").value;
      if (prov === UNLIMITED) { out.push(UNLIMITED); return; }
      if (!prov) return;
      var city = row.querySelector(".loc-city").value;
      var county = row.querySelector(".loc-county").value;
      out.push([prov, city, county].filter(Boolean).join("-"));
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
    locationList.appendChild(makeLocationRow(UNLIMITED));
    syncLocationUI();
  }

  // ---------- 初始化（先加载省市区数据） ----------
  fetch("/static/pca.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      pcaData = data || [];
      titleList.appendChild(makeTitleRow("设计师"));
      titleList.appendChild(makeTitleRow("产品经理"));
      locationList.appendChild(makeLocationRow(UNLIMITED));
      refreshButtons();
    })
    .catch(function () {
      // 数据加载失败时降级：仍渲染空表单
      titleList.appendChild(makeTitleRow("设计师"));
      titleList.appendChild(makeTitleRow("产品经理"));
      locationList.appendChild(makeLocationRow(UNLIMITED));
      refreshButtons();
    });
})();
