<template>
<el-menu
    :default-active="$route.path"
    :router="true"
  class="el-menu-demo"
  mode="horizontal"
  @select="handleSelect"
  background-color="#f9fafb"
  text-color="#4b5563"
  active-text-color="#22949e"
  height="100%">
  <el-menu-item v-for="item in menuList" :key="item.name" :index="item.path">{{ item.name }}</el-menu-item>

</el-menu>

</template>

<script>
export default {
    data(){
        return {
            menuList: [
                {
                    name: '智能体工具集',
                    path: '/aitools'
                },
                {
                    name: '数字员工',
                    path: '/digitstaff'
                }
            ]
        }
    },
    computed: {
        // ...mapState({
        // isCollapse: (state) => state.navCollapse.isCollapse,
        // menuData:state=>state.systemMuneData.menuData
        // }),
    },
    methods: {
        handleSelect(key) {
            console.log(key);
            this.$router.push(key);
        }
    },
    created() {
        // 如果当前路径是根路径，重定向到 /aitools
        if (this.$route.path === '/') {
            this.$router.push('/aitools');
        }
    }
}
</script>

<style>
.el-menu.el-menu--horizontal {
    border-bottom: none;
}
.el-menu{
    margin-left: 10px;
}
.el-dropdown-menu__item, .el-menu-item {
    font-size: 16px;
    padding: 0 15px;
    cursor: pointer;
}
.el-menu.el-menu--horizontal {
    border-bottom: none !important;
}
.el-dropdown-menu__item, .el-menu-item {
    font-size: 16px !important;
}
/* .el-menu--horizontal>.el-menu-item:not(.is-disabled):focus, .el-menu--horizontal>.el-menu-item:not(.is-disabled):hover, .el-menu--horizontal>.el-submenu .el-submenu__title:hover {
    background-color: #e58c8c;
} */
</style>