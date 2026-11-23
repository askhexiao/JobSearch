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
  var unsubWrap = document.getElementById("unsub-wrap");
  var unsubLink = document.getElementById("unsub-link");
  var statusEl = document.getElementById("status");

  var isManage = location.pathname.indexOf("/manage") !== -1;
  var manageEmail = new URLSearchParams(location.search).get("email") || "";

  var pcaData = []; // 省-市数据

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

  // ---------- 工作地点（省-市联动，无删除） ----------
  function makeLocationRow(initialProvince) {
    var row = document.createElement("div");
    row.className = "location-row";

    var prov = document.createElement("select");
    prov.className = "loc-province";
    var city = document.createElement("select");
    city.className = "loc-city";
    city.disabled = true;
    city.style.display = "none";

    // 省：新增行加「请选择省」，首行默认「不限」
    if (initialProvince !== UNLIMITED) {
      prov.appendChild(makeOption("", "请选择省"));
    }
    prov.appendChild(makeOption(UNLIMITED, UNLIMITED));
    pcaData.forEach(function (p) { prov.appendChild(makeOption(p.name, p.name)); });
    prov.value = initialProvince || "";

    city.appendChild(makeOption("", "请选择市"));

    prov.addEventListener("change", function () { onProvinceChange(row); });

    row.appendChild(prov);
    row.appendChild(city);
    return row;
  }

  function onProvinceChange(row) {
    var prov = row.querySelector(".loc-province");
    var city = row.querySelector(".loc-city");
    city.innerHTML = "";

    if (!prov.value || prov.value === UNLIMITED) {
      city.disabled = true;
      city.style.display = "none";
      syncLocationUI();
      return;
    }

    var p = pcaData.find(function (x) { return x.name === prov.value; });
    city.style.display = "";
    city.disabled = false;
    city.appendChild(makeOption("", "请选择市"));
    (p ? p.children : []).forEach(function (c) { city.appendChild(makeOption(c.name, c.name)); });
    syncLocationUI();
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

  // ---------- 管理模式：预填 + 退订 ----------
  function fillLocation(path) {
    if (!path || path === UNLIMITED) {
      locationList.appendChild(makeLocationRow(UNLIMITED));
      return;
    }
    var parts = path.split("-");
    var prov = parts[0] || "";
    var city = parts[1] || "";
    var row = makeLocationRow(prov);
    onProvinceChange(row);
    if (city) {
      row.querySelector(".loc-city").value = city;
    }
    locationList.appendChild(row);
  }

  function loadSubscription(email) {
    fetch("api/subscription?email=" + encodeURIComponent(email))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.error) { setStatus("未找到该订阅", false); return; }
        document.getElementById("email").value = d.email;
        titleList.innerHTML = "";
        (d.titles && d.titles.length ? d.titles : [""]).forEach(function (t) {
          titleList.appendChild(makeTitleRow(t));
        });
        locationList.innerHTML = "";
        if (d.location_unlimited) {
          locationList.appendChild(makeLocationRow(UNLIMITED));
        } else if (d.locations && d.locations.length) {
          d.locations.forEach(fillLocation);
        } else {
          locationList.appendChild(makeLocationRow(UNLIMITED));
        }
        var rt = d.recruit_type || "社招";
        var rb = document.querySelector('input[name="recruit_type"][value="' + rt + '"]');
        if (rb) { rb.checked = true; }
        document.getElementById("employer-db").value = d.employer_db || "";
        document.getElementById("frequency").value = d.frequency || "每周1次";
        document.getElementById("publish-within").value = d.publish_within || "最近1个月";
        submitBtn.textContent = "更新订阅";
        unsubWrap.hidden = false;
        unsubLink.setAttribute("data-email", d.email);
        refreshButtons();
      })
      .catch(function () { setStatus("加载订阅失败", false); });
  }

  unsubLink.addEventListener("click", function (e) {
    e.preventDefault();
    var email = unsubLink.getAttribute("data-email") || manageEmail;
    if (!email) { return; }
    if (!confirm("确定退订？退订后将不再收到职位推送。")) { return; }
    location.href = "unsubscribe?email=" + encodeURIComponent(email);
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
      out.push(city ? (prov + "-" + city) : prov);
    });
    return out;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = document.getElementById("email").value.trim();
    var titles = collectTitles();
    var locations = collectLocations();
    var recruitType = document.querySelector('input[name="recruit_type"]:checked').value;
    var employerDb = document.getElementById("employer-db").value;
    var frequency = document.getElementById("frequency").value;
    var publishWithin = document.getElementById("publish-within").value;

    if (!document.getElementById("consent").checked) {
      setStatus("请先同意隐私说明", false); return;
    }
    if (!email) { setStatus("请输入邮箱", false); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setStatus("请输入正确的邮箱格式", false); return;
    }
    if (titles.length === 0 && locations.length === 0) {
      setStatus("请至少填写一个职位名称或工作地点", false); return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "提交中…";

    fetch("api/subscribe", {
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
        mode: isManage ? "update" : "subscribe",
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          setStatus("✅ " + (res.data.message || "订阅成功！"), true);
          if (!isManage) { resetForm(); }
        } else {
          setStatus((res.data && res.data.error) || "提交失败，请稍后再试", false);
        }
      })
      .catch(function () { setStatus("网络错误，请稍后再试", false); })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = isManage ? "更新订阅" : "立即订阅";
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
  function defaultInit() {
    titleList.appendChild(makeTitleRow("设计师"));
    titleList.appendChild(makeTitleRow("产品经理"));
    locationList.appendChild(makeLocationRow(UNLIMITED));
    refreshButtons();
  }

  fetch("static/pca.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      pcaData = data || [];
      if (isManage && manageEmail) { loadSubscription(manageEmail); }
      else { defaultInit(); }
    })
    .catch(function () {
      if (isManage && manageEmail) { loadSubscription(manageEmail); }
      else { defaultInit(); }
    });
})();
