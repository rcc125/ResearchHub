const {request}=require('../../utils/api');
Page({data:{projects:[],error:''},async onShow(){try{this.setData({projects:await request('/api/v1/projects'),error:''});}catch(e){this.setData({error:e.message});}},openForm(e){wx.navigateTo({url:'/pages/project-form/index?id='+e.currentTarget.dataset.id});}});
