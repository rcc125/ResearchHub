const {request}=require('../../utils/api');
Page({
  data:{projectId:null,title:'',leaderName:'',enrollmentId:null,fields:[],answers:{},saving:false,message:'',error:''},
  async onLoad(opt){const id=Number(opt.id);this.setData({projectId:id});
    try{const res=await request('/api/v1/projects/'+id+'/my-form');const answers=res.answers||{};
      const fields=res.project.form_schema.map(f=>Object.assign({},f,{currentValue:answers[f.key]||'',selectedIndex:f.type==='select'?Math.max(0,(f.options||[]).indexOf(answers[f.key])):0,selectedText:answers[f.key]||''}));
      this.setData({title:res.project.title,leaderName:res.project.leader_name||'',enrollmentId:res.enrollment_id||null,fields,answers});
    }catch(e){this.setData({error:e.message});}
  },
  choose(e){const key=e.currentTarget.dataset.key,fields=this.data.fields;const field=fields.find(f=>f.key===key);const index=Number(e.detail.value),value=field.options[index];
    this.setData({answers:Object.assign({},this.data.answers,{[key]:value}),fields:fields.map(f=>f.key===key?Object.assign({},f,{selectedIndex:index,selectedText:value}):f)});
  },
  textChange(e){const key=e.currentTarget.dataset.key;this.setData({answers:Object.assign({},this.data.answers,{[key]:e.detail.value})});},
  goFirstAppointment(){if(!this.data.enrollmentId){this.setData({error:'请先保存项目表单'});return;}wx.navigateTo({url:'/pages/appointment-create/index?enrollment='+this.data.enrollmentId+'&type=first'});},
  async save(){this.setData({saving:true,error:'',message:''});
    try{const result=await request('/api/v1/projects/'+this.data.projectId+'/my-form','PUT',{answers:this.data.answers});this.setData({enrollmentId:result.enrollment_id,message:'项目专属表单保存成功，可预约首次采集'});}
    catch(e){this.setData({error:e.message});}finally{this.setData({saving:false});}
  }
});
