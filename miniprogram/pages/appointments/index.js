const {request}=require('../../utils/api');
Page({data:{items:[],error:''},onShow(){this.load()},async load(){try{this.setData({items:await request('/api/v1/appointments/me'),error:''})}catch(e){this.setData({error:e.message})}}});
