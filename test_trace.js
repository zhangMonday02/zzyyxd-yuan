const crypto = require('crypto');

/**
 * 模拟人类鼠标轨迹并生成指定格式的 JSON 数据
 * * @returns {Object} 格式完全匹配的传感器数据对象
 */
function generateSensorData() {
    // 1. 初始化基础参数
    const startTime = Date.now();
    
    // 模拟屏幕尺寸 (Screen Info)
    // 格式参考: window.innerWidth, window.innerHeight, pageXOffset, etc.
    // 这里固定一套常见的 1920x1080 屏幕下的浏览器参数，稍微浮动
    const screenW = 1920;
    const screenH = 1080;
    const winW = 1500 + Math.floor(Math.random() * 200);
    const winH = 800 + Math.floor(Math.random() * 100);
    const si = `${winW},${winH},0,${winH - 100},0,${screenH},${screenW},58.8,${winH}`;

    // 2. 设定起点和终点 (模拟用户想去点击某个按钮)
    const startX = 1000 + Math.floor(Math.random() * 100);
    const startY = 50 + Math.floor(Math.random() * 50);
    const endX = 1300 + Math.floor(Math.random() * 50); // 终点 X
    const endY = 900 + Math.floor(Math.random() * 50);  // 终点 Y

    // 3. 生成仿真轨迹 (mp)
    // 使用贝塞尔曲线算法模拟人类的手抖和弧度
    const points = generateHumanPath(startX, startY, endX, endY);
    
    // 4. 格式化 mp (Mouse Path)
    // 格式: x,y,timeDiff,state|...
    const mpArr = points.map(p => `${Math.round(p.x)},${Math.round(p.y)},${p.t},1`);
    const mp = mpArr.join('|');

    // 5. 模拟 mm (Mouse Move - 通常是 mp 的子集或特定状态下的移动)
    // 在你的样本中，mm 的时间戳比 mp 的开始晚。我们取后半段作为 mm
    const splitIndex = Math.floor(points.length * 0.3); 
    const mmArr = points.slice(splitIndex).map(p => `${Math.round(p.x)},${Math.round(p.y)},${p.t},1`);
    const mm = mmArr.join('|');

    // 6. 模拟 mc (Mouse Click)
    // 通常发生在轨迹的最后或接近最后
    const lastP = points[points.length - 1];
    // 格式: x,y,timeDiff, ,1
    const mc = `${Math.round(lastP.x)},${Math.round(lastP.y)},${lastP.t}, ,1`;

    // 7. 模拟 fi (Focus In? 或其他事件)
    // 发生在开始后不久
    const fiTime = points[0].t + Math.floor(Math.random() * 50);
    const fi = `${fiTime},0,1`;

    // 8. 组装最终对象
    return {
        "mc": mc,
        "tc": "", // Touch count/data (桌面端通常为空)
        "mu": "", // Mouse Up (有时为空)
        "te": "", // Touch event
        "mp": mp,
        "tmv": "",
        "mm": mm,
        "ks": "", // Keystroke
        "fi": fi,
        "startTime": startTime,
        "si": si
    };
}

/**
 * 贝塞尔曲线轨迹生成器 (核心算法)
 * 模拟人类移动：有加速、减速和路径抖动
 */
function generateHumanPath(x1, y1, x2, y2) {
    const points = [];
    // 随机控制点，制造弧度
    const cx1 = x1 + (x2 - x1) * 0.3 + (Math.random() - 0.5) * 100;
    const cy1 = y1 + (y2 - y1) * 0.3 + (Math.random() - 0.5) * 100;
    const cx2 = x1 + (x2 - x1) * 0.7 + (Math.random() - 0.5) * 100;
    const cy2 = y1 + (y2 - y1) * 0.7 + (Math.random() - 0.5) * 100;

    // 总耗时 800ms ~ 1500ms
    const totalDuration = 800 + Math.random() * 700;
    // 采样步数
    const steps = 60 + Math.floor(Math.random() * 40);

    for (let i = 0; i <= steps; i++) {
        const t = i / steps; // 0 到 1
        
        // 缓动函数 (Ease-in-out): 模拟起步慢，中间快，收尾慢
        const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

        // 三阶贝塞尔公式
        const x = Math.pow(1 - ease, 3) * x1 + 
                  3 * Math.pow(1 - ease, 2) * ease * cx1 + 
                  3 * (1 - ease) * ease * ease * cx2 + 
                  Math.pow(ease, 3) * x2;
        
        const y = Math.pow(1 - ease, 3) * y1 + 
                  3 * Math.pow(1 - ease, 2) * ease * cy1 + 
                  3 * (1 - ease) * ease * ease * cy2 + 
                  Math.pow(ease, 3) * y2;

        // 当前点的时间偏移
        const timeOffset = Math.floor(totalDuration * t);
        
        // 添加微量抖动 (噪音)，防止轨迹过于完美被判定为机器
        const noiseX = (Math.random() - 0.5) * 2; 
        const noiseY = (Math.random() - 0.5) * 2;

        points.push({
            x: x + noiseX,
            y: y + noiseY,
            t: timeOffset
        });
    }
    return points;
}

// --- 测试运行 ---
const result = generateSensorData();
console.log(JSON.stringify(result, null, 4));