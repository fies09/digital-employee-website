// const { defineConfig } = require('@vue/cli-service')
// module.exports = defineConfig({
//   transpileDependencies: true
// })
const path = require('path')

function resolve(dir) {
  return path.join(__dirname, dir)
}

module.exports = {
  // 关闭eslint检查
  lintOnSave: false,
  
  // 基本路径
  publicPath: '/',
  
  // 开发服务器配置
  devServer: {
    port: 8080,
    open: true,
    host: 'localhost',
    // 代理配置
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    }
  },

  // 生产环境配置
  productionSourceMap: false,
  
  // webpack配置
  chainWebpack: config => {
    // 设置别名
    config.resolve.alias
      .set('@', resolve('src'))
      .set('components', resolve('src/components'))
      .set('views', resolve('src/views'))
      .set('assets', resolve('src/assets'))
      
    // 设置标题
    config.plugin('html')
      .tap(args => {
        args[0].title = '数字员工平台'
        return args
      })
  },

  // 打包输出配置
  outputDir: 'dist',
  assetsDir: 'static'
}