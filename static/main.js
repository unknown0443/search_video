const { createApp } = Vue;

createApp({
  data() {
    return {
      // 채팅/플레이어 관련
      chatInput: "",
      chatMessages: [],
      player: null,

      // 단일 세그먼트 수정 모달
      showModifyModal: false,
      modifySegId: null,
      originalCaption: "",
      originalMembers: [],
      modifyText: "",
      updatedMembers: [],
      memberInput: "",

      // 그룹 수정 모달 (여러 세그먼트)
      showGroupModifyModal: false,
      groupModifySegIds: "",  // 예: "146~148"
      groupOriginalCaption: "",
      groupModifyText: "",
      groupOriginalMembers: [],
      groupUpdatedMembers: [],
      groupMemberInput: "",

      // 병합 모달
      showMergeModal: false,
      mergeSegmentIds: "",
      mergeCaption: "",

      // 분할 모달
      showSplitModal: false,
      splitSegmentId: "",
      splitTime: null,
      splitCaption1: "",
      splitCaption2: "",

      // 생성 모달
      showCreateModal: false,
      createStart: null,
      createEnd: null,
      createCaption: "",

      // "세그먼트" 메뉴 토글
      showSegmentMenu: false,

      // 채팅 모드 (기본은 영상검색 모드)
      chatMode: "search"
    };
  },
  methods: {
    // 채팅 모드 전환 함수
    setChatMode(mode) {
      this.chatMode = mode;
      // 질문 모드일 때 접두어를 붙이지 않고, 기존 입력값 초기화
      this.chatInput = "";
    }
    ,

    // 채팅 전송 (질문 모드인 경우 접두어 추가)
    sendChat() {
      if (!this.chatInput.trim()) return;

      if (this.chatMode === "question" && !this.chatInput.startsWith("질문:")) {
        this.chatInput = "질문: " + this.chatInput;
      }

      this.chatMessages.push({
        sender: "user",
        htmlContent: `<p>${this.escapeHtml(this.chatInput)}</p>`
      });

      axios.post("/chat", { message: this.chatInput })
        .then(res => {
          const botMsg = res.data.response || "";
          const transformed = this.transformLinks(botMsg);
          this.chatMessages.push({
            sender: "bot",
            htmlContent: transformed
          });
          this.$nextTick(() => {
            const container = document.getElementById("chat-messages");
            if (container) container.scrollTop = container.scrollHeight;
          });
        })
        .catch(error => {
          console.error("Error in chat:", error);
          this.chatMessages.push({
            sender: "bot",
            htmlContent: "<p>챗봇 응답 중 오류가 발생했습니다.</p>"
          });
        });
      this.chatInput = "";
    },

    // 링크 변환: 새 포맷 [세그먼트ID=146~148 (start_sec=145.0, end_sec=148.0)]
    transformLinks(text) {
      const reSeg = /\[세그먼트ID=([\d~]+)\s+\(start_sec=(\d+(?:\.\d+)?),\s*end_sec=(\d+(?:\.\d+)?)\)\]/g;
      let replaced = text.replace(reSeg, (match, segid, startSec, endSec) => {
        return `<span class="segment-link" data-segid="${segid}" data-start="${startSec}">[세그먼트 ${segid}]</span>`;
      });
      const reMod = /\[수정하기=([\d~]+)\]/g;
      replaced = replaced.replace(reMod, (match, segid) => {
        return `<span class="modify-link" data-segid="${segid}" style="color:red; text-decoration:underline; cursor:pointer;">수정하기</span>`;
      });
      replaced = replaced.replace(/\n/g, '<br>');
      return replaced;
    },

    escapeHtml(str) {
      return str.replace(/[<>&"]/g, c => {
        switch (c) {
          case '<': return "&lt;";
          case '>': return "&gt;";
          case '&': return "&amp;";
          case '"': return "&quot;";
        }
      });
    },

    initVideoPlayer() {
      const container = document.getElementById("player");
      container.innerHTML = "";
      const videoEl = document.createElement("video");
      videoEl.setAttribute("controls", "controls");
      videoEl.setAttribute("width", "640");
      videoEl.setAttribute("height", "360");
      videoEl.innerHTML = `<source src="/video" type="video/mp4">`;
      container.appendChild(videoEl);
      this.player = videoEl;
    },

    handleSegmentClick(segid, start) {
      const startTime = parseFloat(start) || 0;
      // 1초 전으로 이동 (단, 0보다 작으면 0으로)
      const targetTime = startTime > 1 ? startTime - 1 : 0;
      if (this.player) {
        this.player.currentTime = targetTime;
        this.player.play();
      }
    }
    ,

    // 단일 세그먼트 수정: 그룹이 아닌 경우
    handleModifyClick(segid) {
      if (segid.includes("~")) {
        this.handleGroupModifyClick(segid);
      } else {
        this.modifySegId = segid;
        axios.get(`/segment/${segid}`)
          .then(res => {
            if (res.data.success) {
              const segData = res.data.data;
              const finalCap = segData.manual_caption.trim() || segData.caption.trim();
              this.originalCaption = finalCap;
              this.modifyText = "";
              let members = [];
              segData.faces.forEach(f => {
                if (f.member && !members.includes(f.member)) {
                  members.push(f.member);
                }
              });
              this.originalMembers = members;
              this.updatedMembers = [...members];
              this.memberInput = "";
              this.showModifyModal = true;
            } else {
              alert("세그먼트 정보를 가져오지 못했습니다.");
            }
          })
          .catch(err => {
            console.error("Error fetching segment data:", err);
            alert("세그먼트 정보를 가져오는 중 오류가 발생했습니다.");
          });
      }
    },

    // 그룹 수정: 여러 세그먼트가 묶여 있을 때 (예: "146~148")
    handleGroupModifyClick(segidGroup) {
      this.groupModifySegIds = segidGroup;
      const segIdArray = segidGroup.split("~").map(id => parseInt(id.trim()));
    
      axios.post("/segment/group_info", { segment_ids: segIdArray })
        .then(res => {
          if (res.data.success) {
            // 백엔드에서 받아온 통합 캡션, 멤버 세팅
            this.groupOriginalCaption = res.data.combined_caption;
            this.groupModifyText = "";
            this.groupOriginalMembers = res.data.combined_members;
            this.groupUpdatedMembers = [...res.data.combined_members];
            this.groupMemberInput = "";
            this.showGroupModifyModal = true;
          } else {
            alert("그룹 정보를 가져오지 못했습니다.");
          }
        })
        .catch(err => {
          console.error("Error fetching group info:", err);
          alert("그룹 정보를 가져오는 중 오류가 발생했습니다.");
        });
    }
    ,

    closeModal() {
      this.showModifyModal = false;
    },

    applyModify() {
      const newCaption = this.modifyText.trim() || this.originalCaption;
      const membersString = this.updatedMembers.join(",");
      const overrideCmd = `수정: 세그먼트ID=${this.modifySegId} 내용=${newCaption} 멤버=${membersString}`;
      this.chatMessages.push({
        sender: "user",
        htmlContent: `<p>${this.escapeHtml(overrideCmd)}</p>`
      });
      axios.post("/chat", { message: overrideCmd })
        .then(res => {
          const botMsg = res.data.response || "";
          this.chatMessages.push({
            sender: "bot",
            htmlContent: `<p>${this.escapeHtml(botMsg)}</p>`
          });
          alert("수정이 완료되었습니다.");
        })
        .catch(error => {
          console.error("Error overriding caption/members:", error);
          this.chatMessages.push({
            sender: "bot",
            htmlContent: "<p>캡션/멤버 수정 중 오류가 발생했습니다.</p>"
          });
        });
      this.showModifyModal = false;
    },

    addMember() {
      const newMember = this.memberInput.trim();
      if (newMember && !this.updatedMembers.includes(newMember)) {
        this.updatedMembers.push(newMember);
      }
      this.memberInput = "";
    },
    removeMember(m) {
      this.updatedMembers = this.updatedMembers.filter(x => x !== m);
    },

    // 그룹 수정 모달 관련 메서드
    closeGroupModifyModal() {
      this.showGroupModifyModal = false;
    },
    addGroupMember() {
      const newMember = this.groupMemberInput.trim();
      if (newMember && !this.groupUpdatedMembers.includes(newMember)) {
        this.groupUpdatedMembers.push(newMember);
      }
      this.groupMemberInput = "";
    },
    removeGroupMember(m) {
      this.groupUpdatedMembers = this.groupUpdatedMembers.filter(x => x !== m);
    },
    applyGroupModify() {
      const newCaption = this.groupModifyText.trim() || this.groupOriginalCaption;
      const segIdArray = this.groupModifySegIds.split("~").map(id => id.trim());
      axios.post("/segment/group_modify", {
        segment_ids: segIdArray,
        new_caption: newCaption,
        new_members: this.groupUpdatedMembers
      })
      .then(res => {
        alert(res.data.message);
        this.showGroupModifyModal = false;
      })
      .catch(err => {
        console.error("Error in group modify:", err);
        alert("그룹 수정 중 오류가 발생했습니다.");
      });
    },

    // 병합, 분할, 생성 모달 관련 (기존 그대로)
    openMergeModal() {
      this.mergeSegmentIds = "";
      this.mergeCaption = "";
      this.showMergeModal = true;
      this.showSegmentMenu = false;
    },
    closeMergeModal() {
      this.showMergeModal = false;
    },
    submitMerge() {
      const segmentIds = this.mergeSegmentIds.split(",")
        .map(id => parseInt(id.trim()))
        .filter(id => !isNaN(id));
      axios.post("/segment/merge", {
        segment_ids: segmentIds,
        new_caption: this.mergeCaption
      })
      .then(res => {
        alert(res.data.response);
        this.showMergeModal = false;
      })
      .catch(err => {
        console.error("Merge error:", err);
        alert("세그먼트 병합 중 오류가 발생했습니다.");
      });
    },

    openSplitModal() {
      this.splitSegmentId = "";
      this.splitTime = null;
      this.splitCaption1 = "";
      this.splitCaption2 = "";
      this.showSplitModal = true;
      this.showSegmentMenu = false;
    },
    closeSplitModal() {
      this.showSplitModal = false;
    },
    submitSplit() {
      axios.post("/segment/split", {
        segment_id: parseInt(this.splitSegmentId),
        split_time: this.splitTime,
        captions: [this.splitCaption1, this.splitCaption2]
      })
      .then(res => {
        alert(res.data.response);
        this.showSplitModal = false;
      })
      .catch(err => {
        console.error("Split error:", err);
        alert("세그먼트 분할 중 오류가 발생했습니다.");
      });
    },

    openCreateModal() {
      this.createStart = null;
      this.createEnd = null;
      this.createCaption = "";
      this.showCreateModal = true;
      this.showSegmentMenu = false;
    },
    closeCreateModal() {
      this.showCreateModal = false;
    },
    submitCreate() {
      axios.post("/segment/create", {
        video_id: 1,
        start_time: this.createStart,
        end_time: this.createEnd,
        caption: this.createCaption
      })
      .then(res => {
        alert(res.data.response);
        this.showCreateModal = false;
      })
      .catch(err => {
        console.error("Create error:", err);
        alert("세그먼트 생성 중 오류가 발생했습니다.");
      });
    },

    toggleSegmentMenu() {
      this.showSegmentMenu = !this.showSegmentMenu;
    }
  },
  mounted() {
    this.initVideoPlayer();
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get("q");
    if (query) {
      this.chatInput = query;
      this.sendChat();
    }
    document.addEventListener("click", (evt) => {
      const target = evt.target;
      if (!target) return;
      if (target.classList.contains("segment-link")) {
        const segid = target.getAttribute("data-segid");
        const start = target.getAttribute("data-start");
        this.handleSegmentClick(segid, start);
      } else if (target.classList.contains("modify-link")) {
        const segid = target.getAttribute("data-segid");
        this.handleModifyClick(segid);
      } else if (target.classList.contains("split-link")) {
        const segid = target.getAttribute("data-segid");
        this.splitSegmentId = segid;
        this.splitTime = null;
        this.splitCaption1 = "";
        this.splitCaption2 = "";
        this.showSplitModal = true;
      }
    });
  }
}).mount("#app");
