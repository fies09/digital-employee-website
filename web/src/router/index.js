import Vue from 'vue'
import VueRouter from 'vue-router'
import Home from '../views/home.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home,
    redirect: '/aitools',
    children: [
      {
        path: '/aitools',
        name: 'aitools',
        component: () => import('../views/AiTools/list.vue')
      },
      {
        path: '/digitstaff',
        name: 'digitstaff',
        component: () => import('../views/DigitStaff/index.vue'),
        meta: {
          title: '数字员工'
        }
      }
    ]
  }
]

const router = new VueRouter({
  mode: 'history',
  routes
})
// const VueRouterPush = VueRouter.prototype.push
// VueRouter.prototype.push = function push (to) {
//   return VueRouterPush.call(this, to).catch(err => err)
// }


export default router
