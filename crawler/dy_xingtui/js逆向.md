通过观察接口，我们发现接口中只有一个加密信息sign，
对于这个接口加密我们进行全局搜索sign，发现这个值在多个函数中进行了加密赋值，最终锁定到decodeURIComponent这个关键函数上，
本质上只是对字符串进行了md5加密，那这就很好处理了，只需要再观察观察加密参数即可
我们通过浏览器分析后，执行我们的监控方法，然后模拟一次请求加密函数：

```javascript
window.original_decode = window.decodeURIComponent;

// 2. 覆盖它，植入间谍代码
window.decodeURIComponent = function(str) {
    // 执行原始解码，获取真正喂给 MD5 的内容
    const result = window.original_decode(str);
    
    // 过滤一下噪音，只打印包含 "app_secret" 或 "page" 的关键字符串
    if (str && (typeof str === 'string') && (str.includes('app_secret=') || str.includes('page='))) {
        console.log("%c🕵️ 抓到了！即将进入 MD5 的字符串：", "color: red; font-size: 14px; font-weight: bold;");
        console.log(result); 
    }
    
    return result;
};

console.log("✅ 间谍已部署，请立即运行你的 VC 测试代码！");
VM120217:18 ✅ 间谍已部署，请立即运行你的 VC 测试代码！
undefined
(function() {
    const t = 1766721378;
    const p = {
        page: '1',
        limit: '10',
        sell_num_min: '1000',
        search_type: '11',
        sort_type: '1',
        source: '0',
        platform: 'douyin'
    };
    VC(p, t);
})();
VM120217:11 🕵️ 抓到了！即将进入 MD5 的字符串：
VM120217:12 limit=10&page=1&platform=douyin&search_type=11&sell_num_min=1000&sort_type=1&source=0&time=1766721378&app_secret=68ed5a701a0f44de033d6aa276baf3bb
undefined
```


我们对请求进行还原后：
```javascript

import crypto from 'crypto'

// 1. 密钥配置
const Cfe = '68ed5a701a0f44de033d6aa276baf3bb'
const headerSalt = '0ffbc7210302b0313733b862f3bf7e67'

// 2. 加密工具
const md5Upper = (s) => crypto.createHash('md5').update(s).digest('hex').toUpperCase()
const md5Lower = (s) => crypto.createHash('md5').update(s).digest('hex').toLowerCase()

// 3. 自动同步服务器时间 (避免本地时间误差)
async function getServerTime() {
    try {
        const res = await fetch('https://www.reduxingtui.com', { method: 'HEAD' })
        const serverDate = res.headers.get('date')
        return Math.floor(new Date(serverDate).getTime() / 1000)
    } catch (e) {
        return Math.floor(Date.now() / 1000)
    }
}

// 4. 修正后的 VC 签名函数
function VC(params, t) {
    // 步骤 A: 仅合并业务参数和时间 (不包含 app_secret)
    const n = { ...params, time: t }

    // 步骤 B: 排序并拼接
    let o = Object.keys(n)
        .sort() // 字典序排序 (limit 在前, time 在后)
        .map((k) => `${k}=${n[k]}`)
        .join('&')

    // 步骤 C: 必须把 app_secret 拼接在最后！
    o = `${o}&app_secret=${Cfe}`

    // 打印一下，确保和浏览器抓到的一模一样
    console.log('本地生成的待加密串:', o)

    // 步骤 D: 加密
    return md5Upper(o) // 这里去掉了 decodeURIComponent，因为手动拼接通常不需要反转义
}

function Sfe(t) {
    return md5Lower(String(t) + headerSalt)
}

// 5. 执行请求
async function run() {
    // 自动获取服务器时间
    const timestamp = await getServerTime()
    console.log('服务器时间:', timestamp)

    const businessParams = {
        page: '1',
        limit: '10',
        sell_num_min: '1000',
        search_type: '11',
        sort_type: '1',
        source: '0',
        platform: 'douyin',
    }

    // 计算签名
    const urlSign = VC(businessParams, timestamp)
    const headerSign = Sfe(timestamp)

    // 拼接 URL
    const endpoint = '/api/douke/search'
    const url = new URL(`https://www.reduxingtui.com${endpoint}`)
    Object.keys(businessParams).forEach((k) => url.searchParams.append(k, businessParams[k]))
    url.searchParams.append('time', timestamp)
    url.searchParams.append('sign', urlSign)

    // 构造 Header
    const headers = {
        accept: 'application/json, text/plain, */*',
        'authori-zation': 'Bearer 45114cedfddd64db6b0c5f0acf929487', // 确认 Token 有效性
        'form-type': 'pc',
        sign: headerSign,
        timestamp: String(timestamp),
        referer: 'https://www.reduxingtui.com/',
        cookie: 'think_lang=zh-cn; PHPSESSID=ce151308cca93454c283240fa981d10b',
        'user-agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }

    try {
        const response = await fetch(url.toString(), { headers })
        const data = await response.json()
        console.log('✅ 响应结果:', JSON.stringify(data, null, 2))
    } catch (e) {
        console.error('❌ 请求异常:', e)
    }
}

await run()

```