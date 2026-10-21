const {request}=require('../../utils/api');
Page({
  data:{name:'',genders:['男','女','不愿透露'],genderIndex:0,birthDate:'',today:'',height:'',weight:'',bmi:'--',subjectCode:'',saving:false,message:'',error:''},
  async onLoad(){
    const now=new Date(); const today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-'); this.setData({today});
    try {const data=await request('/api/v1/subjects/me');if(data.profile){let p=data.profile;
      this.setData({name:p.name||'',subjectCode:p.subject_code,genderIndex:Math.max(0,this.data.genders.indexOf(p.gender)),birthDate:p.birth_date,height:String(p.height_cm),weight:String(p.weight_kg)});this.calcBmi();}}
    catch(e){if(String(e.message).includes('401')||e.message.includes('登录'))wx.redirectTo({url:'/pages/login/index'});else this.setData({error:e.message});}
  },
  nameChange(e){this.setData({name:e.detail.value});},
  genderChange(e){this.setData({genderIndex:Number(e.detail.value)});},
  birthChange(e){this.setData({birthDate:e.detail.value});},
  heightChange(e){this.setData({height:e.detail.value});this.calcBmi();},
  weightChange(e){this.setData({weight:e.detail.value});this.calcBmi();},
  calcBmi(){const h=Number(this.data.height)/100,w=Number(this.data.weight);this.setData({bmi:h>0&&w>0?(w/h/h).toFixed(1):'--'});},
  async save(){
    const d=this.data;
    if(!d.name.trim()||!d.birthDate||!(Number(d.height)>50&&Number(d.height)<=250)||!(Number(d.weight)>10&&Number(d.weight)<=350)){
      this.setData({error:'请填写姓名、出生日期、身高和体重'});return;
    }
    this.setData({saving:true,error:'',message:''});
    try{const res=await request('/api/v1/subjects/me','PUT',{name:d.name.trim(),gender:d.genders[d.genderIndex],birth_date:d.birthDate,height_cm:Number(d.height),weight_kg:Number(d.weight)});
      this.setData({name:res.profile.name,subjectCode:res.profile.subject_code,message:'保存成功，可继续选择科研项目'});
    }catch(e){this.setData({error:e.message});}
    finally{this.setData({saving:false});}
  },
  goProjects(){wx.switchTab({url:'/pages/projects/index'});}
});
