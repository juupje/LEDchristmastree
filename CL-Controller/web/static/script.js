function get_value_output(name) {
    var obj = document.getElementById(name)
    if(obj) {
        var output = document.getElementById(name+"_output")
        if(output)
            return [output, obj.value];
    }
    return null;
}

function slider_update(name) {
    let res = get_value_output(name);
    if(res)
        res[0].innerHTML = Number.isInteger(res[1]) ? res[1] : Number.parseFloat(res[1]).toFixed(2);
}

function color_update(name) {
    let res = get_value_output(name);
    if(res)
        res[0].innerHTML = res[1];
}

function send_data(method, url, data) {
    let xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4) {
            if(xhr.status != 200) {
                alert("Got error: " + xhr.status);
            }
            let response = JSON.parse(xhr.responseText);
            if(response["success"] == true) {
                let box = document.getElementById("popup");
                let content = box.children[0];
                content.innerHTML = "success!";
                box.classList.remove("hide-popup");
                setTimeout(() => {
                    box.classList.add("hide-popup");
                }, 1000);
            } else
                alert("Er ging iets mis...\n" + response["message"]);
        }
    }
    xhr.send(JSON.stringify(data));
}

function stop_animation() {
    rpi_command('stop', true, '/anim/');
}

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? parseInt(result[1], 16) +"," + parseInt(result[2], 16) + "," +parseInt(result[3], 16) : "255,255,255";
}
function collect_values(form_name, names) {
    var table = document.getElementById(form_name);
    var values = {};
    var inputs = table.getElementsByTagName("input");
    for(var i = 0; i < names.length; i++) {
        for(var j = 0; j < inputs.length; j++) {
            if(inputs[j].name == names[i]) {
                let input = inputs[j];
                if(input.type == 'range')
                    values[names[i]] = Number(input.value);
                else if(input.type == 'checkbox')
                    values[names[i]] = input.checked;
                else if(input.type == 'color') {
                    //first, check if there is a drop-down associated with this
                    let dd = document.querySelector('input[name="drop-down_'+names[i]+'"]:checked');
                    if(!dd || dd.value=="other")
                        values[names[i]] = hexToRgb(input.value);
                    else
                        values[names[i]] = document.querySelector('input[name="drop-down_'+names[i]+'"]:checked').value;
                } else if(input.type == 'radio')
                    values[names[i]] = document.querySelector('input[name="drop-down_'+names[i]+'"]:checked').value;
                else
                    values[names[i]] = input.value;
                break;
            } else if(inputs[j].name == "drop-down_"+names[i]) {
                values[names[i]] = document.querySelector('input[name="drop-down_'+names[i]+'"]:checked').value;
            }
        }
    }
    console.log("Collected values:",values);
    return values;
}

function rpi_command(key_name, value, url) {
    let xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4) {
            if(xhr.status != 200) {
                alert("Got error: " + xhr.status);
            }
            let response = JSON.parse(xhr.responseText);
            if(response["success"] == true) {
                let box = document.getElementById("popup");
                let content = box.children[0];
                content.innerHTML = "success!";
                box.classList.remove("hide-popup");
            } else
                alert("Something went wrong...\n" + response["message"]);
        }
    }
    data = {};
    data[key_name] = value;
    xhr.send(JSON.stringify(data));
}

function color_preset_changed(name, option) {
    //find the corresponding color input
    let input = document.getElementById(name);
    if(option=="other") {
        input.style.display = "block";
    } else {
        input.style.display = "none";
    }
}

function toggle_preset_dialog(anim_name) {
    let preset_div = document.getElementById("preset_dialog");
    if(preset_div.style.display == "block") { // close menu
        preset_div.style.display = "none";
    } else { // open menu
        //populate elements
        let xhr = new XMLHttpRequest();
        xhr.open("GET", "/presets/animation/"+anim_name, true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onreadystatechange = function() {
            if(xhr.readyState == 4) {
                if(xhr.status != 200) {
                    alert("Got error: " + xhr.status);
                }
                let response = JSON.parse(xhr.responseText);
                console.log(response);
                // add response elements to select
                let select = document.getElementById("preset_select");
                let select_btn = document.getElementById("select-btn");
                select.innerHTML = "";
                for (let i = 0; i < response.length; i++) {
                    let opt = document.createElement("option");
                    opt.value = response[i]["id"];
                    opt.innerHTML = response[i]["name"];
                    select.appendChild(opt);
                }
                if(response.length == 0) {
                    let opt = document.createElement("option");
                    opt.value = "none";
                    opt.innerHTML = "No presets available";
                    select.appendChild(opt);
                    select.disabled = true;
                    select_btn.disabled = true;
                } else {
                    select.disabled = false;
                    select_btn.disabled = false;
                }
            }
        }
        xhr.send();
        preset_div.style.display = "block";
    }
}

function close_preset_dialog(save) {
    let preset_div = document.getElementById("preset_dialog");
    preset_div.style.display = "none";
    if(save) {
        let preset_id = document.getElementById("preset_select").value;
        if(preset_id == "none")
            return;
        document.location.href = "/home?animation="+anim_name+"&preset="+preset_id;
        /*let xhr = new XMLHttpRequest();
        xhr.open("GET", "/presets/"+preset_id, true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onreadystatechange = function() {
            if(xhr.readyState == 4) {
                if(xhr.status != 200) {
                    alert("Got error: " + xhr.status);
                }
                let response = JSON.parse(xhr.responseText);
                console.log(response);
                let data = JSON.parse(response["json"]);
                let anim_name = response["animation"];
            }
        }
        xhr.send();*/
    }
}

function save_preset(preset_id, anim_name, data) {
    preset_name = prompt("Enter a name for the preset:", "");
    if(preset_name.length==0) {
        alert("That's not a valid name");
        return;
    }
    req = {"json": data, "animation": anim_name, "name": preset_name};
    let xhr = new XMLHttpRequest();
    xhr.open("POST", "/presets/" + (preset_id != null ? preset_id : "create"), true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function() {
        if(xhr.readyState == 4) {
            if(xhr.status != 201) {
                alert("Got error: " + xhr.status);
            }
            let response = JSON.parse(xhr.responseText);
            if(response["success"] == true) {
                let box = document.getElementById("popup");
                let content = box.children[0];
                content.innerHTML = "success!";
                box.classList.remove("hide-popup");
                setTimeout(() => {
                    box.classList.add("hide-popup");
                }, 1000);
            } else
                alert("Something went wrong...\n" + response["message"]);
        }
    }
    xhr.send(JSON.stringify(req));
}