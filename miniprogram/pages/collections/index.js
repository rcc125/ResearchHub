const {request}=require('../../utils/api');
Page({data:{items:[],error:''},onShow(){this.load()},async load(){try{this.setData({items:await request('/api/v1/collections/me'),error:''})}catch(e){this.setData({error:e.message})}},
 book(e){wx.navigateTo({url:'/pages/appointment-create/index?enrollment='+e.currentTarget.dataset.enrollment+'&collection='+e.currentTarget.dataset.collection})},
 appointments(){wx.navigateTo({url:'/pages/appointments/index'})}});
