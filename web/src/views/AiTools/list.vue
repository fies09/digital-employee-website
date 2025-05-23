<template>
  <div>
    <div class="tools-list" v-for="type in agentTypes" :key="type">
      <el-divider content-position="left">
        <span class="type-text">{{ type }}</span>
      </el-divider>
      <el-row>
        <el-col
          :span="3"
          style="margin-left: 10px; min-width: 190px"
          v-for="agent in getAgentsByType(type)"
          :key="agent.name"
        >
        
          <el-card
            shadow="hover"
            :body-style="{  padding: '10px' }"
            style="margin: 10px"
            @click.native="open(agent.url)"
          >
            <div class="agent-header">
              <el-avatar
                style="min-width: 50px"
                shape="square"
                :size="50"
                :src="agent.agentUrl"
              />
              <strong class="agent-name">{{ agent.name }}</strong>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script>
export default {
    data() {
        return {
        agentList: [
        {
          name: "视频脚本生成器",
          agentUrl: require("../../assets/aiimg/视频脚本生成器.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=8r9149apo32seo3znlt0xpyf",
          type: "工具",
        },
        {
          name: "网页内容摘要",
          agentUrl: require("../../assets/aiimg/网页内容摘要.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=yzfc3340gs7xq1xv4lx5935g",
          type: "工具",
        },
        {
          name: "思维导图生成",
          agentUrl: require("../../assets/aiimg/思维导图生成.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=vgzbrx9ax98jrpynz0r76cik",
          type: "内容",
        },
        {
          name: "抖音账号分析",
          agentUrl: require("../../assets/aiimg/抖音账号分析.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=g1soqyf40fp7ehzs0ngzyydc",
          type: "运营",
        },
        {
          name: "PPT生成助手",
          agentUrl: require("../../assets/aiimg/PPT生成助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=9ttiblgoko2gg06fuiom6co1",
          type: "内容",
        },
        {
          name: "抖音热点选题",
          agentUrl: require("../../assets/aiimg/抖音热点选题.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=y4xkxlgdj97lmf5n8rzs7xj7",
          type: "运营",
        },
        {
          name: "AI证件照",
          agentUrl: require("../../assets/aiimg/AI证件照.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=j0dubd9pd889cmnjlxq6y4h1",
          type: "工具",
        },
        {
          name: "合同审核助手",
          agentUrl: require("../../assets/aiimg/合同审核助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=dfsdhy1hifyobguwsmk2gdii",
          type: "工具",
        },
        {
          name: "一键海报设计",
          agentUrl: require("../../assets/aiimg/一键海报设计.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=q7rk6eudaqtp75sbwlxa8vcm",
          type: "运营",
        },
        {
          name: "直播策划方案",
          agentUrl: require("../../assets/aiimg/直播策划方案.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=7natkgyl5f29w53t62bz8a1h",
          type: "运营",
        },
        {
          name: "LOGO生成",
          agentUrl: require("../../assets/aiimg/LOGO生成.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=zzj6jpeeuphvo7dn2uwz7rd2",
          type: "工具",
        },
        {
          name: "公众号文案编写助手",
          agentUrl: require("../../assets/aiimg/公众号文案编写助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=d6ildisnved4mhi932asmyw4",
          type: "文案",
        },
        {
          name: "专业律师",
          agentUrl: require("../../assets/aiimg/专业律师.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=hwpe7dcu3ycm24j3sdigakig",
          type: "工具",
        },
        {
          name: "直播话术神器",
          agentUrl: require("../../assets/aiimg/直播话术神器.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=s7nn6qx6gq1eabngcxl1g9h5",
          type: "运营",
        },
        {
          name: "公文写作助手",
          agentUrl: require("../../assets/aiimg/公文写作助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=0uyenqov7mejvljcr7g2blcj",
          type: "文案",
        },
        {
          name: "短视频文案神器",
          agentUrl: require("../../assets/aiimg/短视频文案神器.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=631r7tk5e1ht0oqxnl4etjuu",
          type: "文案",
        },
        {
          name: "万能英语助手",
          agentUrl: require("../../assets/aiimg/万能英语助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=sshr6uvzuswkj8xvz6c9vlzf",
          type: "工具",
        },
        {
          name: "知识图谱生成神器",
          agentUrl: require("../../assets/aiimg/知识图谱生成神器.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=ztzjuvsxssvqydtie31nlr5p",
          type: "内容",
        },
        {
          name: "直播运营智能体",
          agentUrl: require("../../assets/aiimg/直播运营智能体.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=ao31ryprovqh6rublmo3a48h",
          type: "运营",
        },
        {
          name: "产品卖点提炼工具",
          agentUrl: require("../../assets/aiimg/产品卖点提炼工具.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=ammnhwrnouq7vu9bzth8lyui",
          type: "运营",
        },
        {
          name: "智能分析助手",
          agentUrl: require("../../assets/aiimg/智能分析助手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=i6ilqnvd6v08ccvxh0vdh71u",
          type: "工具",
        },
        {
          name: "AI引流大师",
          agentUrl: require("../../assets/aiimg/AI引流大师.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=ydk59sft113qn94gxt00cxn0",
          type: "运营",
        },
        {
          name: "短视频口播带货高手",
          agentUrl: require("../../assets/aiimg/短视频口播带货高手.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=po4ehtw3ehj9rzc5i6ybr2ya",
          type: "运营",
        },
        {
          name: "SWOT专家",
          agentUrl: require("../../assets/aiimg/SWOT专家.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=2iom6wyaygpjcx7fkattgryt",
          type: "内容",
        },
        {
          name: "教培销售话术教练",
          agentUrl: require("../../assets/aiimg/教培销售话术教练.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=h1ca7gh376ygq8fdlohj0ham",
          type: "文案",
        },
        {
          name: "无人直播带货精灵",
          agentUrl: require("../../assets/aiimg/无人直播带货精灵.png"),
          url: "http://47.109.107.249:3000/chat/share?shareId=8qbav8dqy21p8d55eeg0vu9c",
          type: "内容",
        },
      ],
    }
  },
  computed: {
    agentTypes() {
      return [...new Set(this.agentList.map(agent => agent.type))]
    }
  },
  methods: {
    getAgentsByType(type) {
      return this.agentList.filter(agent => agent.type === type)
    },
    open(url) {
      console.log('Opening URL:', url);
      if (!url) {
        console.error('URL is empty or undefined');
        return;
      }
      try {
        window.open(url, '_blank');
      } catch (error) {
        console.error('Error opening URL:', error);
      }
    }
  }
}
</script>

<style>
.tools-list {
  margin: 20px 0;
}

.el-divider__text {
  font-size: 20px;
  font-weight: bold;
}

.agent-header {
  display: flex;
  align-items: center;
}

.agent-name {
  font-size: 16px;
  font-weight: bold;
  padding-left: 10px;
  word-break: break-all;
}

.type-text {
  font-weight: bold;
  font-size: 20px;
}

.el-card {
  transition: all 0.3s;
}

.el-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);
}
</style>