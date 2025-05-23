<template>
<el-container>
  <el-header height="70px">
    <img class="logo" src="@/assets/logo16_9.png" alt="logo" srcset="">
    <Header />
  </el-header>
  <el-main>
    <router-view></router-view>
  </el-main>
</el-container>
</template>

<script>
// @ is an alias to /src
import Header from '@/views/Layout/Header.vue'

export default {
  name: 'HomeView',
  components: {
    Header
  }
}
</script>
<style>
  .el-header, .el-footer {
    background-color: #fbfcfd;
    color: #333;
    text-align: center;
    line-height: 70px;
  }
  .el-header{
    margin: 15px;
    border: 1px solid #e5e7eb;
    border-radius: 5px;
    display: flex;
    align-items: center;
  }
  
  .el-aside {
    background-color: #fbfcfd;
    color: #333;
    text-align: center;
    line-height: 200px;
  }
  
  .el-main {
    margin: 15px;
    background-color: #fff;
    color: #333;
    text-align: center;
    padding: 0 !important;
    /* line-height: 160px; */
  }
  
  body > .el-container {
    margin-bottom: 40px;
  }
  
  .el-container:nth-child(5) .el-aside,
  .el-container:nth-child(6) .el-aside {
    line-height: 260px;
  }
  
  .el-container:nth-child(7) .el-aside {
    line-height: 320px;
  }

  .logo{
    width: 55px;
    height: 55px;
  }
</style>
