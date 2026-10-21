const {request}=require('../../utils/api');
Page({data:{enrollment:0,collection:0,type:'reschedule',date:'',time:'14:00',note:'',workdaysText:'周一至周五',workdayStart:'09:00',workdayEnd:'17:00',message:'',error:''},
 onLoad(opt){this.setData({enrollment:Number(opt.enrollment),collection:Number(opt.collection||0),type:opt.type||'reschedule'});this.loadProjectSchedule(Number(opt.enrollment));},
 async loadProjectSchedule(enrollment){try{const p=await request('/api/v1/enrollments/'+enrollment+'/context');this.setData({workdaysText:p.workdays_text||'周一至周五',workdayStart:p.workday_start||'09:00',workdayEnd:p.workday_end||'17:00'});}catch(e){this.setData({error:e.message})}}
 ,dateChange(e){this.setData({date:e.detail.value})},timeChange(e){this.setData({time:e.detail.value})},noteChange(e){this.setData({note:e.detail.value})},
 async submit(){if(!this.data.date){this.setData({error:'请选择预约日期'});return;}try{const body={enrollment_id:this.data.enrollment,appointment_type:this.data.type,requested_at:this.data.date+'T'+this.data.time+':00',note:this.data.note};if(this.data.type==='reschedule')body.previous_collection_id=this.data.collection;await request('/api/v1/appointments','POST',body);wx.showToast({title:'提交成功',icon:'success'});wx.redirectTo({url:'/pages/appointments/index'});
 }catch(e){this.setData({error:e.message})}}});
