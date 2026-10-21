const { BASE_URL } = require('./config');
function request(path, method='GET', data) {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token');
    wx.request({ url: BASE_URL + path, method, data,
      header: Object.assign({'Content-Type':'application/json'}, token ? {Authorization:'Bearer '+token}:{}),
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(new Error(typeof res.data.detail === 'string' ? res.data.detail : '请求失败：'+res.statusCode));
      },
      fail(err) { reject(new Error('网络连接失败，请检查后端是否启动及本地调试设置')); }
    });
  });
}
module.exports = {request};
