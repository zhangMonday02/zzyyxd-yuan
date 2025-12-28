require('./crypto-js')
const {Sign} = require("./sign");

function AESCBCEncrypt_RES(data, key) {
    const keyHex = CryptoJS.enc.Utf8.parse(key)
    const ivHex = CryptoJS.enc.Utf8.parse("0123456789ABCDEF")
    const encrypted = CryptoJS.AES.encrypt(data, keyHex, {
        iv: ivHex,
        mode: CryptoJS.mode.CBC,
        padding: CryptoJS.pad.Pkcs7
    })
    return encrypted.toString()
}

function convertEnvToArray(env1, deviceConfig, dynamic_key, now_ts) {
    // 辅助函数：处理数组格式
    const formatArray = (arr) => {
        if (Array.isArray(arr)) {
            // 如果是二维数组，使用JSON格式
            if (Array.isArray(arr[0])) {
                return JSON.stringify(arr);
            }
            // 如果是一维数组，用方括号包裹
            return `[${arr.join(',')}]`;
        }
        return arr;
    };

    // 辅助函数：处理对象，取前两个值
    const formatObject = (obj) => {
        if (typeof obj === 'object' && obj !== null) {
            const values = Object.values(obj);
            return values.slice(0, 2); // 只取前两个值
        }
        return [obj];
    };

    // 根据env1的键和输出数组的顺序定义映射
    return [
        // 前13个值
        env1.dghfh565 || "",            // "W.10050"
        String(env1.asdfasdf || ""),     // "1.5"
        String(env1.sdfgsdf || ""),      // "11"
        "",                              // 空字符串（占位）
        env1.asdfccv || "",              // "Blink"
        env1.sdfg433 || "",              // "Win32"
        env1.sdfgsf4 || "",              // "Chrome"
        env1.sdfgfds4 ? env1.sdfgfds4.replace("140.0.0.0", "143.0.0.0") : "143.0.0.0", // 版本号替换
        String(env1.asdfd6 || ""),       // "504"
        formatArray(env1.cvxgfh6 || []), // 数组格式
        String(env1.nvbcn65 || false),   // "false"
        String(env1.hdgfh65 || ""),      // "1.5"

        // 处理dfgjdf65对象，取两个值
        ...formatObject(env1.dfgjdf65 || {}),

        // 处理gdfsg对象，取所有值
        ...Object.values(env1.gdfsg || {}).slice(0, 5).map(v => String(v || "")),

        // 继续其他值
        env1.gdfhvcb6 || "",             // "cb81e6d3309daa1dec9a6fc3edc7ca7f"
        String(env1.fhgjgfhd675 || ""),  // "104"
        dynamic_key || "",               // 动态key
        String(env1.vbmnbn67 ? "8" : env1.vbmnbn67 || ""), // 固定为"8"
        env1.vbjghj7 || "",              // "0*0*50*0"
        String(env1.vbnmbn3 || ""),      // "24"
        String(env1.dfxvsdf4 || ""),     // "24"
        env1.asdfadsf34 || "",           // "srgb"
        String(env1.cvbncv6 || false),   // "false"
        String(env1.fghgf6 || false),    // "false"
        String(env1.jhgkjgh || false),   // "false"
        String(env1.cvfbbv2 || ""),      // "0"
        String(env1.fghjcv3 || ""),      // "0"
        env1.vbnmvbn4 ? "cb00626a032d01f53c7804479a626d6a" : "", // 替换值
        env1.fghjfgh5 || "",             // ""
        String(env1.a87sg9 ? "24" : env1.a87sg9 || ""), // 固定为"24"
        formatArray(env1.dfghfg64 || []), // 二维数组格式
        env1.lk4n6ll || "",              // "Windows"
        env1.zvcxv234 || "",             // "10"

        // 处理fghjgh78对象，取两个值
        ...formatObject(env1.fghjgh78 || {}),

        // 继续其他值
        env1.fghjghs || "",              // "zh-CN"
        env1.fghjfghe || "",             // "Asia/Shanghai"
        deviceConfig.ip || "",           // 设备IP
        env1.nghjdfgsh || "",            // ""
        String(env1.csdfgdfd || true),   // "true"
        String(env1.tyjhtyge || true),   // "true"
        String(env1.jcvhve || true),     // "true"
        env1.dfghcbn || "",              // "1067*1707"
        String(env1.ihgnghyt || true),   // "true"

        // 处理jghkghjk对象，先取三个值，然后是"15"
        ...formatObject(env1.jghkghjk || {}),
        "15",                             // 固定值

        // 继续其他值
        "0a980a9fa1de263b43be86d59566c598d5988b83de263cf063", // 固定hash值

        // 处理wdfghcgv对象
        env1.wdfghcgv?.gfdhfg67 || "",   // URL
        env1.wdfghcgv?.gfdhfg67 || "",   // 重复URL
        env1.wdfghcgv?.fghjhg763 ? "275*1707" : "", // 固定尺寸
        env1.wdfghcgv?.ghjkghj5678 || "", // "1019*1707"
        env1.wdfghcgv?.fghjnb254 || "",  // "1019*1707"
        String(env1.wdfghcgv?.gfhjfgh567 || ""), // "0"
        env1.wdfghcgv?.kghjjh657 ? "275*1692" : "", // 固定尺寸
        String(env1.wdfghcgv?.wertwer67 || true), // "true"

        "",                               // 空字符串
        String(env1.wertwer || false),    // "false"
        env1.wertdxfgs ? env1.wertdxfgs.replace("140.0.0.0", "143.0.0.0") : "143.0.0.0", // 版本号替换
        env1.sdfghtrh ? env1.sdfghtrh.replace("140.0.0.0", "143.0.0.0") : "", // User-Agent替换
        env1.sdfgfdghjf || "",           // "unspecified"
        String(env1.hdfghgf || false),   // "false"
        env1.gfdsfd675 || "",            // "saf-captcha"
        String(env1.gdfggc || ""),       // "0"
        formatArray(env1.gfdb5456 || []), // 数组格式
        String(env1.asf65445 || ""),     // "-480"
        env1.gfdc6456 || "",             // 随机字符串
        String((now_ts - 3000 + 230) || ""), // 时间戳计算
        env1.gdffd98u9 || "",            // 随机字符串
        String((now_ts - 3000 + 500) || ""), // 时间戳计算
        env1.fvcb343 || "",              // "desktop"
        String(env1.xcvbrt454 || false), // "false"
        "",                               // 空字符串
        env1.bytrre54 || "",             // hash
        env1.rewtq2354 || "",            // hash

        // 处理adfvcx234对象
        ...formatObject(env1.adfvcx234 || {}),

        // 处理cxv902832对象，取两个值加上设备IP
        ...formatObject(env1.cxv902832 || {}),
        deviceConfig.ip || "",           // 设备IP
        "",                               // 空字符串

        // 继续数值字段
        String(env1.gdfgs23145 || ""),   // "0"
        String(env1.h9w87s9 || ""),      // "0"
        deviceConfig.timestamp || "",    // 设备时间戳
        "MCMwIzAjMCMwIzAjMCMwIzAjMSMwIzAjMCMwIzAjMCMwIzAjMCMwIzEjMCMxMTExMTExMDExMTExMTExMTExMTExMTExMQ==", // 固定base64

        // 一系列数值字段（简化处理）
        String(env1.cvxhgftw312 || ""),  // "1"
        String(env1.vcvbtryr43 || ""),   // "1"
        String(env1.hgdf53425 || true),  // "true"
        String(env1.dfasf345 || ""),     // "1"
        String(env1.dafs3455d || ""),    // "1"
        String(env1.gfdg3424 || ""),     // "1"
        String(env1.fxcv342 || ""),      // "1"
        String(env1.xc12 || ""),         // "1"
        String(env1.qwergfd32 || ""),    // "1"
        String(env1.dfg645 || ""),       // "1"
        String(env1.vc234 || ""),        // "1"
        String(env1.vv4c234 || ""),      // "1"
        String(env1.fd324 || ""),        // "1"
        String(env1.cxv324g || ""),      // "1"
        String(env1.nhtret || ""),       // "1"
        String(env1.vbgfx342 || ""),     // "1"
        String(env1.dr5435 || ""),       // "1"
        String(env1.vcx4321 || ""),      // "1"
        String(env1.q9qs8g7 || ""),      // "1"
        String(env1.asdjf789 || ""),     // "1"
        String(env1.gs8d67g9 || ""),     // "0"

        // 处理数组
        formatArray(env1.as78f5 || []),

        // 最后几个值
        env1.e09baa || "",               // 固定字符串
        String(env1.dsfdsf423 || ""),    // "0"
        String(env1.asdfdfg4536 || ""),  // "0"
        String(env1.dfghfgd2345 || ""),  // "0"
        String(env1.hjfgkghj657 || "")   // "0"
    ].map(item => String(item)); // 确保所有值都是字符串
}


const FINGERPRINT_CONFIG = {
    userAgents: [
        // --- Windows 10/11 Chrome (Recent & Future) ---
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            version: "143.0.0.0",
            fullVersion: "143.0.6099.109"
        },
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            version: "131.0.0.0",
            fullVersion: "131.0.6778.86"
        },
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            version: "130.0.0.0",
            fullVersion: "130.0.6723.58"
        },
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            version: "129.0.0.0",
            fullVersion: "129.0.6668.101"
        },

        // --- Windows 10/11 Edge ---
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            version: "143.0.0.0",
            fullVersion: "143.0.6167.85"
        },
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            version: "131.0.0.0",
            fullVersion: "131.0.2903.51"
        },
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            version: "130.0.0.0",
            fullVersion: "130.0.2849.46"
        },

        // --- Windows 11 Specific (Note: UA string usually still says NT 10.0, but keeping distinct entries for rotation) ---
        {
            ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            version: "132.0.0.0",
            fullVersion: "132.0.6834.6" // Canary/Dev
        }
    ],

    gpus: [
        // --- NVIDIA High End (Desktop) ---
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.15.3118)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.15.3623)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.7212)"
        },

        // --- NVIDIA Mid Range (Very Common) ---
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.15.4601)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.7168)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.6140)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.7141)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)"
        },

        // --- NVIDIA Laptop (Mobile) ---
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3050 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.14.9709)"
        },
        {
            vendor: "Google Inc. (NVIDIA)",
            renderer: "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.6259)"
        },

        // --- Intel Integrated (Crucial for simulating office laptops/ultrabooks) ---
        {
            vendor: "Google Inc. (Intel)",
            renderer: "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.101.1994)"
        },
        {
            vendor: "Google Inc. (Intel)",
            renderer: "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.100.8681)"
        },
        {
            vendor: "Google Inc. (Intel)",
            renderer: "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.101.4502)"
        },

        // --- AMD ---
        {
            vendor: "Google Inc. (AMD)",
            renderer: "ANGLE (AMD, AMD Radeon RX 6600 XT Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.13023.1012)"
        },
        {
            vendor: "Google Inc. (AMD)",
            renderer: "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.1034.6)"
        },
        {
            vendor: "Google Inc. (AMD)",
            renderer: "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.11028.10001)"
        } // Ryzen APU
    ],

    resolutions: [
        // Standard Desktop
        {w: 1920, h: 1080},
        {w: 2560, h: 1440},
        {w: 1366, h: 768},

        // Laptop Common
        {w: 1536, h: 864},
        {w: 1440, h: 900},
        {w: 1280, h: 720},

        // High DPI / 4K
        {w: 3840, h: 2160},
        {w: 2560, h: 1600}, // MacBook Pro styled or 16:10 monitors

        // Ultrawide
        {w: 3440, h: 1440},

        // Portrait / Vertical (Developers/Mobile sim)
        {w: 1080, h: 1920},
        {w: 1067, h: 1707}
    ],

    memory: [4, 8, 12, 16, 24, 32, 64], // Added 4 (Low end), 12 (Odd), 64 (Workstation)

    concurrency: [2, 4, 6, 8, 12, 16, 20, 24, 32] // Added 2 (Low end), 6 (Common AMD/Intel), 20 (Intel 12th+ gen)
};


// 指纹生成辅助函数
function randomItem(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function randomHex(len) {
    let output = '';
    for (let i = 0; i < len; i++) {
        output += Math.floor(Math.random() * 16).toString(16);
    }
    return output;
}

function randomString(len) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < len; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

// 生成浏览器指纹（内置函数，不再读取文件）
function generateFingerprint() {
    const selectedUA = randomItem(FINGERPRINT_CONFIG.userAgents);
    const selectedGPU = randomItem(FINGERPRINT_CONFIG.gpus);
    const selectedRes = randomItem(FINGERPRINT_CONFIG.resolutions);
    const memory = randomItem(FINGERPRINT_CONFIG.memory);
    const cores = randomItem(FINGERPRINT_CONFIG.concurrency);
    const now = Date.now();

    const fp = {
        "dghfh565": "W.10050",
        "asdfasdf": 1.5,
        "sdfgsdf": 11,
        "asdfccv": "Blink",
        "sdfg433": "Win32",
        "sdfgsf4": "Chrome",
        "sdfgfds4": selectedUA.version, // 使用 143.0.0.0，后续会被替换
        "asdfd6": 504,
        "cvxgfh6": ["application/pdf", "text/pdf"],
        "nvbcn65": false,
        "hdgfh65": 1.5,
        "dfgjdf65": {
            "fhgjjghdf": selectedGPU.vendor,
            "xcvdfgfd": selectedGPU.renderer
        },
        "gdfsg": {"xcvbbc65": "", "fghf657": "", "ghhjf656": 0, "xdgfd6545": 0, "Whfgjhgj76": 0},
        "gdfhvcb6": randomHex(32),
        "fhgjgfhd675": 104,
        "v78d98s": "aGRtMDFoNGc=",
        "vbmnbn67": memory,
        "vbjghj7": "0*0*50*0",
        "vbnmbn3": 24,
        "dfxvsdf4": 24,
        "asdfadsf34": "srgb",
        "cvbncv6": false,
        "fghgf6": false,
        "jhgkjgh": false,
        "cvfbbv2": 0,
        "fghjcv3": 0,
        "vbnmvbn4": randomHex(32),
        "fghjfgh5": "",
        "a87sg9": cores, // 注意：Log2_Data.js 中会将其固定为 "24"
        "dfghfg64": [["audioinput", ""], ["videoinput", ""], ["audiooutput", ""]],
        "lk4n6ll": "Windows",
        "zvcxv234": "10",
        "fghjgh78": {"fdsaf4415": 1, "hgdfhgf437": true},
        "fghjghs": "zh-CN",
        "fghjfghe": "Asia/Shanghai",
        "ifghjgfhjp": "117.153." + Math.floor(Math.random() * 255) + "." + Math.floor(Math.random() * 255), // IP地址，会被 deviceConfig.ip 替换
        "nghjdfgsh": "",
        "csdfgdfd": true,
        "tyjhtyge": true,
        "jcvhve": true,
        "dfghcbn": `${selectedRes.w}*${selectedRes.h}`,
        "ihgnghyt": true,
        "jghkghjk": {"asdfd4545": 0, "jghfjfhg453": false, "dfsgdf87": false},
        "dfghfgdh6": "",
        "wdfghcgv": {
            "gfdhfg67": "https://www.wjx.cn/mobile/smslogin.aspx",
            "sdfgd435": "",
            "fghjhg763": `${selectedRes.w}*${selectedRes.h - 40}`,
            "ghjkghj5678": `${selectedRes.w}*${selectedRes.h}`,
            "fghjnb254": `${selectedRes.w}*${selectedRes.h}`,
            "gfhjfgh567": 0,
            "kghjjh657": `${selectedRes.w}*${selectedRes.h - 140}`,
            "wertwer67": true
        },
        "wertwer": false,
        "wertdxfgs": "140.0.0.0", // 会被替换为 143.0.0.0
        "sdfghtrh": selectedUA.ua, // 包含版本号，会被替换
        "sdfgfdghjf": "unspecified",
        "hdfghgf": false,
        "gfdsfd675": "saf-captcha",
        "gdfggc": 0,
        "gfdb5456": ["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer", "Microsoft Edge PDF Viewer", "WebKit built-in PDF"],
        "asf65445": -480,
        "gfdc6456": randomString(40),
        "hgvh4435": now,
        "gdffd98u9": randomString(42),
        "fvcb343": "desktop",
        "xcvbrt454": false,
        "bytrre54": randomHex(32),
        "rewtq2354": randomHex(32),
        "adfvcx234": {
            "xcvbwre": selectedUA.ua.replace("Mozilla/", ""), // 包含版本号，会被替换
            "cxvczv21eqw": "Mozilla"
        },
        "cxv902832": {"adfac23": "64", "zcxv232r4": selectedUA.fullVersion}, // 包含版本号，会被替换
        "gdfgs23145": 0,
        "h9w87s9": 0,
        "v8w7102": now - Math.floor(Math.random() * 500),
        "bgnb89435": "",
        "cvxhgftw312": 1,
        "vcvbtryr43": 1,
        "hgdf53425": true,
        "dfasf345": 1,
        "dafs3455d": 1,
        "gfdg3424": 1,
        "fxcv342": 1,
        "xc12": 1,
        "qwergfd32": 1,
        "dfg645": 1,
        "vc234": 1,
        "vv4c234": 1,
        "fd324": 1,
        "cxv324g": 1,
        "nhtret": 1,
        "vbgfx342": 1,
        "dr5435": 1,
        "vcx4321": 1,
        "q9qs8g7": 1,
        "asdjf789": 1,
        "gs8d67g9": 0,
        "as78f5": ["Chromium", "Not=A?Brand", "Google Chrome"],
        "e09baa": "0|0|0|0|0|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0",
        "dsfdsf423": 0,
        "asdfdfg4536": 0,
        "dfghfgd2345": 0,
        "hjfgkghj657": 0
    };
    return fp;
}


function getLog2Data(data, dynamic_key, config, env) {

    key = config.key

    params3 = 'saf-captcha'
    res_params3 = AESCBCEncrypt_RES(params3, key)
    params4 = 'W.10050'
    res_params4 = AESCBCEncrypt_RES(params4, key)
    now_ts = +Date.now()
    params5 = now_ts + ''
    res_params5 = AESCBCEncrypt_RES(params5, key)
    dynamic_key = dynamic_key
    deviceConfig = config

    // env1 = {
    //     "dghfh565": "W.10050",
    //     "asdfasdf": 1.5,
    //     "sdfgsdf": 11,
    //     "asdfccv": "Blink",
    //     "sdfg433": "Win32",
    //     "sdfgsf4": "Chrome",
    //     "sdfgfds4": "140.0.0.0",
    //     "asdfd6": 504,
    //     "cvxgfh6": [
    //         "application/pdf",
    //         "text/pdf"
    //     ],
    //     "nvbcn65": false,
    //     "hdgfh65": 1.5,
    //     "dfgjdf65": {
    //         "fhgjjghdf": "Google Inc. (NVIDIA)",
    //         "xcvdfgfd": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.15.3699)"
    //     },
    //     "gdfsg": {
    //         "xcvbbc65": "",
    //         "fghf657": "",
    //         "ghhjf656": 0,
    //         "xdgfd6545": 0,
    //         "Whfgjhgj76": 0
    //     },
    //     "gdfhvcb6": "cb81e6d3309daa1dec9a6fc3edc7ca7f",
    //     "fhgjgfhd675": 104,
    //     "v78d98s": "aGRtMDFoNGc=",
    //     "vbmnbn67": 4,
    //     "vbjghj7": "0*0*50*0",
    //     "vbnmbn3": 24,
    //     "dfxvsdf4": 24,
    //     "asdfadsf34": "srgb",
    //     "cvbncv6": false,
    //     "fghgf6": false,
    //     "jhgkjgh": false,
    //     "cvfbbv2": 0,
    //     "fghjcv3": 0,
    //     "vbnmvbn4": "5b276e605b26c9c0c683b8a9a90f909d",
    //     "fghjfgh5": "",
    //     "a87sg9": 28,
    //     "dfghfg64": [
    //         [
    //             "audioinput",
    //             ""
    //         ],
    //         [
    //             "videoinput",
    //             ""
    //         ],
    //         [
    //             "audiooutput",
    //             ""
    //         ]
    //     ],
    //     "lk4n6ll": "Windows",
    //     "zvcxv234": "10",
    //     "fghjgh78": {
    //         "fdsaf4415": 1,
    //         "hgdfhgf437": true
    //     },
    //     "fghjghs": "zh-CN",
    //     "fghjfghe": "Asia/Shanghai",
    //     "ifghjgfhjp": "117.153.23.139",
    //     "nghjdfgsh": "",
    //     "csdfgdfd": true,
    //     "tyjhtyge": true,
    //     "jcvhve": true,
    //     "dfghcbn": "1067*1707",
    //     "ihgnghyt": true,
    //     "jghkghjk": {
    //         "asdfd4545": 0,
    //         "jghfjfhg453": false,
    //         "dfsgdf87": false
    //     },
    //     "dfghfgdh6": "",
    //     "wdfghcgv": {
    //         "gfdhfg67": "https://www.wjx.cn/mobile/smslogin.aspx",
    //         "sdfgd435": "",
    //         "fghjhg763": "339*1707",
    //         "ghjkghj5678": "1019*1707",
    //         "fghjnb254": "1019*1707",
    //         "gfhjfgh567": 0,
    //         "kghjjh657": "339*1692",
    //         "wertwer67": true
    //     },
    //     "wertwer": false,
    //     "wertdxfgs": "140.0.0.0",
    //     "sdfghtrh": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    //     "sdfgfdghjf": "unspecified",
    //     "hdfghgf": false,
    //     "gfdsfd675": "saf-captcha",
    //     "gdfggc": 0,
    //     "gfdb5456": [
    //         "PDF Viewer",
    //         "Chrome PDF Viewer",
    //         "Chromium PDF Viewer",
    //         "Microsoft Edge PDF Viewer",
    //         "WebKit built-in PDF"
    //     ],
    //     "asf65445": -480,
    //     "gfdc6456": "CJvqvRdf0mI1pE4t5b4sm4TjheK529KHJvtDGYCn",
    //     "hgvh4435": 1766058246804,
    //     "gdffd98u9": "nzRGBpEbdPI20erHBqg2WzO573HNMKfZZaCbAIl4VT",
    //     "fvcb343": "desktop",
    //     "xcvbrt454": false,
    //     "bytrre54": "9d4568c009d203ab10e33ea9953a0264",
    //     "rewtq2354": "99914b932bd37a50b983c5e7c90ae93b",
    //     "adfvcx234": {
    //         "xcvbwre": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    //         "cxvczv21eqw": "Mozilla"
    //     },
    //     "cxv902832": {
    //         "adfac23": "64",
    //         "zcxv232r4": "140.0.7339.127"
    //     },
    //     "gdfgs23145": 0,
    //     "h9w87s9": 0,
    //     "v8w7102": "1766058246370",
    //     "bgnb89435": "",
    //     "cvxhgftw312": 1,
    //     "vcvbtryr43": 1,
    //     "hgdf53425": true,
    //     "dfasf345": 1,
    //     "dafs3455d": 1,
    //     "gfdg3424": 1,
    //     "fxcv342": 1,
    //     "xc12": 1,
    //     "qwergfd32": 1,
    //     "dfg645": 1,
    //     "vc234": 1,
    //     "vv4c234": 1,
    //     "fd324": 1,
    //     "cxv324g": 1,
    //     "nhtret": 1,
    //     "vbgfx342": 1,
    //     "dr5435": 1,
    //     "vcx4321": 1,
    //     "q9qs8g7": 1,
    //     "asdjf789": 1,
    //     "gs8d67g9": 0,
    //     "as78f5": [
    //         "Chromium",
    //         "Not=A?Brand",
    //         "Google Chrome"
    //     ],
    //     "e09baa": "0|0|0|0|0|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0",
    //     "dsfdsf423": 0,
    //     "asdfdfg4536": 0,
    //     "dfghfgd2345": 0,
    //     "hjfgkghj657": 0
    // }

    env1 = generateFingerprint()

    env_params_arr = convertEnvToArray(
        env1,
        {
            ip: deviceConfig.ip,
            timestamp: deviceConfig.timestamp
        },
        dynamic_key, // dynamic_key
        now_ts   // now_ts
    );

    env_params = env_params_arr.join('#')

    // env_params = `W.10050#1.5#11#Apple#WebKit#Win32#Edge#143.0.0.0#0#[application/pdf,text/pdf]#false#3#Google Inc. (NVIDIA)#ANGLE (NVIDIA, NVIDIA GeForce RTX 5060 Laptop GPU (0x00002D59) Direct3D11 vs_5_0 ps_5_0, D3D11)###0#0#0#7ac740c429098467302ad4335b3aa561#104#${dynamic_key}#8#0*0*0*0#24#24#srgb#false#false#false#0#0#cb00626a032d01f53c7804479a626d6a##24#[[audioinput,],[videoinput,],[audiooutput,]]#iOS#18.5#1#true#zh-CN#Asia/Shanghai#${deviceConfig.ip}##true#true#true#932*430#true#1#true#true#8df8ede263379eafc92c9cf370cd9698d59c3585de263fc92c#https://www.wjx.cn/mobile/smslogin.aspx##932*430#932*430#932*430#0#932*430#true##false#605.1.15#Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/143.0.0.0#unspecified#false#saf-captcha#0#[PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF]#-480#8OLCbIkR4UV72FVwr6ByvSaB8OlOS4KRLCRec6Fr#${now_ts - 3000 + 230}#0p4ZX9b0cQwIygeSQtbzYfYHPZ3fIOOyC4hXrBqCgE#${now_ts - 3000 + 230}#mobile#false##9d4568c009d203ab10e33ea9953a0264#99914b932bd37a50b983c5e7c90ae93b#5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/143.0.0.0#Mozilla####0#0#${deviceConfig.timestamp}#MSMwIzAjMCMwIzAjMCMwIzAjMCMxIzAjMCMwIzAjMCMwIzAjMCMwIzEjMCMxMTExMTExMDExMTExMTExMTExMTExMTExMQ==#1#1#true#1#1#1#1#1#1#1#1#1#1#1#1#1#1#1#1#0#0#[]#0|0|0|0|0|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0|1|1|0#0`
    res_params2 = AESCBCEncrypt_RES(env_params, key)
    raw_data = [
        deviceConfig.sessionId,
        res_params2,
        res_params3,
        res_params4,
        "",
        res_params5
    ].join("#")
    // res_data = AESCBCEncrypt_RES(raw_data, "a549a55c60a39aa0")

    btoa_res = btoa(raw_data)

    res_final_params = "W.10050#saf-captcha#q0hcfsca"

    res_final_params = AESCBCEncrypt_RES(res_final_params, key)

    // res_final = [
    //     "ab034ec0643f91399eb33e062dc7fae1",
    //     "W",
    //     res_final_params,
    //     "W20220202",
    //     "CLOUD",
    //     "91",
    //     "501",
    //     btoa_res
    // ].join('#')

    res_final = [
        "ab034ec0643f91399eb33e062dc7fae1",
        "W",
        res_final_params,
        "W20220202",
        "CLOUD",
        "58",
        "501",
        btoa_res
    ].join('#')

    res_data = AESCBCEncrypt_RES(res_final, "a549a55c60a39aa0")

    const {Sign} = require('./sign')
    data['Data'] = res_data
    data = Sign(data, 'fpOKzILEajkqgSpr9VvU98FwAgIRcX')

    // data = formatToQueryString(data)

    return data
}


function formatToQueryString(obj) {
    const params = [];

    // 按照字母顺序排序键（阿里云API通常需要排序）
    const sortedKeys = Object.keys(obj);

    for (const key of sortedKeys) {
        let value = obj[key];

        // 确保值是字符串
        if (value !== null && value !== undefined) {
            value = String(value);

            // URL编码：特殊字符如 +, /, = 需要编码
            // 注意：Data字段中的 '+' 需要编码为 %2B
            const encodedValue = encodeURIComponent(value)
                .replace(/\+/g, '%2B')   // 加号
                .replace(/\//g, '%2F')   // 斜杠
                .replace(/'/g, '%27')    // 单引号
                .replace(/"/g, '%22')    // 双引号
                .replace(/\(/g, '%28')   // 左括号
                .replace(/\)/g, '%29');  // 右括号

            params.push(`${key}=${encodedValue}`);
        }
    }

    return params.join('&');
}

