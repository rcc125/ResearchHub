// 本地开发者工具模拟器：后端在本机运行。真机需要改成可访问的 HTTPS 域名。
const BASE_URL = 'http://127.0.0.1:8000';
// 仅用于本地演示，正式环境必须设为 false，并配置有效小程序 AppID。
const DEMO_MODE = true;
module.exports = { BASE_URL, DEMO_MODE };
