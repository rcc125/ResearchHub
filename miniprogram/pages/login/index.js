const {request}=require('../../utils/api');
const {DEMO_MODE}=require('../../utils/config');
Page({
  data:{loading:false,error:'',modeText:DEMO_MODE?'本地演示登录':'微信登录'},
  async login(){
    this.setData({loading:true,error:''});
    try {
      let result;
      if(DEMO_MODE){result=await request('/api/v1/auth/demo','POST',{});}
      else {
        const res=await new Promise((resolve,reject)=>wx.login({success:resolve,fail:reject}));
        if(!res.code) throw new Error('未获取到微信登录 code');
        result=await request('/api/v1/auth/wechat','POST',{code:res.code});
      }
      wx.setStorageSync('token', result.access_token);
      wx.switchTab({url:'/pages/personal-center/index'});
    }catch(e){this.setData({error:e.message||'登录失败'});}
    finally{this.setData({loading:false});}
  }
});
