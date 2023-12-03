/*jshint esversion: 6 */
let button;
let advanceButton;
let outputDiv;
let periodsForm;
let periodsInput;
let loginForm;
let usernameInput;
let passwordInput;
let buttons;
let readout;
let currentHeading;
let temperatureMap = {};
let INTERVAL_UPDATE = 3000;
let system_data;
let allSystems;
let interval;
let programOutput = "";
let temperatureOutput = "";
let currentTarget;
let relayOn;
let t;

const withinOneSecond = (time) => {
  const currentTime = moment();
  return currentTime.diff(time, "seconds") === 1;
};

async function updateTemperatureMap() {
  if (!allSystems) {
    return;
  }
  if (withinOneSecond(temperatureMap.lastUpdated)) {
    return;
  }
  for (const system of allSystems) {
    const id = system.system_id;
    const temp = await getTemperature(id);
    temperatureMap[id] = temp;
  }
  temperatureMap.lastUpdated = moment();
}

async function setReadout() {
  if (!allSystems) return;
  if (Object.keys(temperatureMap).length === 0) await updateTemperatureMap();
  const elems = [];
  for (const system of allSystems) {
    const temp = temperatureMap[system.system_id];
    const str = `${system.system_id}: ${temp}˚C`;
    const elem = document.createElement("h3");
    elem.innerHTML = str;
    elems.push(elem);
  }
  readout.innerHTML = "";
  for (const elem of elems) {
    readout.appendChild(elem);
  }
}

const periodHelper =
  '<span class="period-helper"><br>[[startHour, endHour, targetTemp], ...]</span>';

function getSystems() {
  return fetch(`/api/v3/systems/`).then((response) =>
    response.json().then((data) => {
      if (response.status === 200) {
        return sortData(data);
      } else {
        button.disabled = true;
        throw new Error(`${response.status}`);
      }
    })
  );
}

function setProgramOutput() {
  if (!system_data) {
    return "";
  }
  programOutput = system_data.program === true ? "Program: ON" : "Program: OFF";
  return programOutput;
}

function toggleUIElements() {
  if (!t) {
    periodsForm.style.display = "none";
    button.style.display = "none";
    buttons.style.display = "none";
    button.style.display = "none";
    advanceButton.style.display = "none";
    outputDiv.style.display = "none";
    currentHeading.style.display = "none";
    loginForm.style.display = "block"; // Show login form when not logged in
    return;
  }
  loginForm.style.display = "none";
  buttons.style.display = "block";

  if (!system_data) {
    button.style.display = "none";
    advanceButton.style.display = "none";
    periodsForm.style.display = "none";
    currentHeading.style.display = "none";
    outputDiv.innerHTML = "";
    return;
  }
  button.style.display = "block";
  advanceButton.style.display = "block";
  if (system_data.advance) {
    advanceButton.style.fontWeight = "bold";
    advanceButton.disabled = true;
  } else {
    advanceButton.style.fontWeight = "normal";
    advanceButton.disabled = false;
  }
  currentHeading.style.display = "block";
  currentHeading.innerText =
    system_data.system_id.substring(0, 1).toUpperCase() +
    system_data.system_id.substring(1);
  outputDiv.style.display = "block";
  outputDiv.innerHTML = `${setProgramOutput()}${temperatureOutput}`;
  if (!system_data?.program) {
    periodsForm.style.display = "none";
  } else {
    periodsForm.style.display = "block";
  }
}

function setSystem(system_id) {
  programOutput = "";
  system_data = allSystems.find((system) => system.system_id === system_id);
  if (!system_data) {
    return;
  }
  toggleUIElements();
  update(system_data.system_id);
  const button1 = Array.from(buttons.children).find(
    (button) => button.innerHTML === system_data.system_id
  );
  const buttons2 = Array.from(buttons.children).filter(
    (button) => button.innerHTML !== system_data.system_id
  );
  button1.style.fontWeight = "bold";
  button1.style.boxShadow = "0 0 10px 2px rgba(255, 255, 255, 0.3)";
  buttons2.forEach((button) => {
    button.style.fontWeight = "normal";
    button1.style.boxShadow = "none";
  });
  button.innerHTML = system_data.program === false ? "ENABLE" : "DISABLE";
  button.disabled = false;
  periodsInput.value = system_data.program
    ? JSON.stringify(system_data.periods.map((p) => [p.start, p.end, p.target]))
    : "";
  console.log(system_data.periods);
  periodsInput.disabled = !system_data || !system_data.program;
  outputDiv.innerHTML = `${setProgramOutput()}${temperatureOutput}`;
  setTemperatureOutput();
}

function logout() {
  t = undefined;
  localStorage.clear();
  window.location.reload();
}

function updatePeriod(event) {
  event.preventDefault();
  const systemId = system_data.system_id;
  if (!systemId) {
    return;
  }
  const method = "POST";

  let periods = JSON.parse(periodsInput.value);
  periods = periods.map((p) => ({
    start: p[0],
    end: p[1],
    target: p[2],
  }));

  const body = JSON.stringify({ periods });
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch(`/api/v3/periods/${systemId}/`, { method, headers, body }).then(
    function (response) {
      if (response.status !== 200) {
        logout();
      }
      response
        .json()
        .then(function (json) {
          system_data = json;
        })
        .then(() => {
          getSystems()
            .then((data) => (allSystems = data))
            .then(() => setSystem(system_data.system_id));
        });
    }
  );
}

function triggerAdvance() {
  const systemId = system_data.system_id;
  if (!systemId) {
    return;
  }
  const method = "POST";
  const body = JSON.stringify({ end_time: Date.now() / 1000 + 60 * 60 });
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch(`/api/v3/advance/${systemId}/`, { method, headers, body }).then(
    function (response) {
      if (response.status !== 200) {
        logout();
      }
      response.json().then(function (json) {
        system_data = json;
        getSystems()
          .then((data) => {
            allSystems = data;
          })
          .then(() => toggleUIElements());
      });
    }
  );
}

function getTemperature(system) {
  return fetch(`/api/v3/temperature/${system}/`).then((response) =>
    response.json().then((data) => {
      if (response.status === 200) {
        temperatureOutput = "";
        return data.temperature;
      }
      button.disabled = true;
      throw new Error(`${response.status}`);
    })
  );
}

function getTargetInfo(system) {
  return fetch(`/api/v3/target/${system}/`).then((response) =>
    response.json().then((data) => {
      if (response.status === 200) {
        temperatureOutput = "";
        return data;
      }
      button.disabled = true;
      throw new Error(`${response.status}`);
    })
  );
}

function setTemperatureOutput() {
  temperatureOutput = "";
  if (programOutput.length > 0) {
    temperatureOutput += "<br><br>";
  }
  temperatureOutput += `Temperature: ${JSON.stringify(
    temperatureMap[system_data.system_id]
  )}˚C ${!!currentTarget || relayOn ? "/" : ""} ${currentTarget || ""} ${
    relayOn ? "🔥" : ""
  }`;
  outputDiv.innerHTML = `${programOutput}${temperatureOutput}`;
}

function update(system) {
  updateWrapper(system);
}

function onClick() {
  const headers = new Headers({
    "Content-Type": "application/json",
    Authorization: `${t.token_type} ${t.access_token}`,
  });
  fetch("/api/v3/systems/", {
    method: "POST",
    headers,
    body: JSON.stringify({
      system_id: system_data.system_id,
      program: !system_data.program,
    }),
  }).then((response) => {
    if (response.status === 200) {
      getSystems().then((data) => {
        allSystems = data;
        setSystem(system_data.system_id);
      });
      updateInterval();
      resetInterval();
    } else {
      logout();
    }
  });
}

function updateInterval() {
  if (!system_data) {
    return;
  }
  update(system_data.system_id);
}

function resetInterval() {
  clearInterval(interval);
  interval = setInterval(updateInterval, INTERVAL_UPDATE);
}

function idClickHandler(event, s) {
  setSystem(s.system_id);
  resetInterval();
}

function login(e) {
  e.preventDefault();
  const formData = new FormData();
  formData.set("username", usernameInput.value);
  formData.set("password", passwordInput.value);

  fetch("/token/", {
    method: "POST",
    body: formData,
  }).then((result) =>
    result.json().then((data) => {
      if (result.status !== 200) {
        logout();
      }
      t = data;
      localStorage.setItem("t", JSON.stringify(t));
      if (t) {
        loginForm.style.display = "none";
      }
      toggleUIElements();
    })
  );
}

function sortData(data) {
  return data.sort((a, b) => {
    if (a.system_id < b.system_id) {
      return -1;
    }
    if (a.system_id > b.system_id) {
      return 1;
    }
    return 0;
  });
}

function updateWrapper(system) {
  updateTemperatureMap()
    .then(setReadout)
    .then(() => getTargetInfo(system))
    .then((data) => {
      currentTarget = data.current_target;
      relayOn = data.relay_on;
      setTemperatureOutput();
    });
}

function getAndSetSystem(systemId) {
  getSystems().then((data) => {
    allSystems = data;
    setSystem(systemId);
  });
  updateInterval();
  resetInterval();
}

function createSystemButtons(allSystems) {
  for (const s of allSystems) {
    const button = document.createElement("button");
    button.innerHTML = s.system_id;
    button.addEventListener("click", (event) => idClickHandler(event, s));
    buttons.appendChild(button);
    buttons.style.display = "none";
  }
}

window.onload = () => {
  button = document.querySelector("#program");
  advanceButton = document.querySelector("#advance");
  outputDiv = document.querySelector("#output");
  periodsForm = document.querySelector("#periodsForm");
  periodsInput = document.querySelector("#new_periods");
  loginForm = document.querySelector("#loginForm");
  usernameInput = document.querySelector("#username");
  passwordInput = document.querySelector("#password");
  buttons = document.querySelector("#buttons");
  readout = document.querySelector("#readout");
  currentHeading = document.querySelector("#current-system");
  t = JSON.parse(localStorage.getItem("t") ?? "null");
  toggleUIElements();
  periodsForm.addEventListener("submit", updatePeriod);
  loginForm.addEventListener("submit", login);
  button.addEventListener("click", () =>
    getAndSetSystem(system_data.system_id)
  );

  getSystems().then((data) => {
    allSystems = data;
    createSystemButtons(allSystems);
    setReadout().then(() => toggleUIElements());
  });
};

updateInterval();
resetInterval();
