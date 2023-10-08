import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import TestComponent from "../components/TestComponent.vue"
import TextPostForm from "../views/TextPostForm.vue"
import PhotoPostForm from "../views/PhotoPostForm.vue"
import Login from "../views/Login.vue"
import CornaCreateForm from "../views/CornaCreateForm.vue"

Vue.use(VueRouter)

const router = new VueRouter({
  mode: 'history',
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue')
    },
    {
      path:"/test",
      name: "test",
      component: TestComponent,
      props: true
    },
    {
      path:"/p/text",
      name: "text-post",
      component: TextPostForm,
      props: true
    },
    {
      path:"/p/photo",
      name: "photo-post",
      component: PhotoPostForm
    },
    {
      path:"/login",
      name: "login",
      component: Login,
      props: true
    },
    {
      path:"/create-corna",
      name: "create-corna",
      component: CornaCreateForm,
      props: true
    },
  ]
})

export default router
