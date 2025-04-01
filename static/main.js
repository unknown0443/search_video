const { createApp } = Vue;

createApp({
  data() {
    return {
      // 채팅/플레이어 관련
      chatInput: "",
      chatMessages: [],
      player: null,

      // 자막 수정 모달
      showModifyModal: false,
      modifySegId: null,

      // 기존 캡션 / 멤버
      originalCaption: "",
      originalMembers: [],

      // 새 캡션 / 수정 멤버
      modifyText: "",
      updatedMembers: [],
      memberInput: "",

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

      // 추가: 채팅 모드 (기본은 영상검색 모드)
      // "search": 영상검색 모드, "question": 질문 모드
      chatMode: "search"
    };
  },
  methods: {
    // 채팅 모드 전환 함수
    setChatMode(mode) {
      this.chatMode = mode;
      if(mode === "question") {
        this.chatInput = "질문: ";
      } else {
        this.chatInput = "";
      }
    },

    // 채팅 전송 (질문 모드인 경우 접두어 추가)
    sendChat() {
      if (!this.chatInput.trim()) return;
    
      // 질문 모드라면 "질문:" 접두어가 없을 때만 추가
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
          const splitted = transformed.split(/(?=<span[^>]*class="segment-link")/g);
          splitted.forEach(part => {
            part = part.trim();
            if (part) {
              this.chatMessages.push({
                sender: "bot",
                htmlContent: part
              });
            }
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
    
      // 모드를 search로 되돌리지 않음!
      // this.chatMode = "search";  // 제거
    
      this.chatInput = "";
    },

    // 기존 검색 결과 내 링크 변환
    transformLinks(text) {
      const reSeg = /\[세그먼트ID=(\d+)\s+start=(\d+(?:\.\d+)?)\]/g;
      let replaced = text.replace(reSeg, (match, segid, start) => {
        return `<span class="segment-link" data-segid="${segid}" data-start="${start}">[세그먼트 ${segid}]</span>`;
      });
      const reMod = /\[수정하기=(\d+)\]/g;
      replaced = replaced.replace(reMod, (match, segid) => {
        return `
          <span class="modify-link" data-segid="${segid}" style="color:red; text-decoration:underline; cursor:pointer;">수정하기</span>
        `;
      });
      return replaced;
    },

    // HTML 이스케이프 함수
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

    // 비디오 플레이어 초기화
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

    // 세그먼트 클릭: 영상 이동
    handleSegmentClick(segid, start) {
      const startTime = parseFloat(start) || 0;
      if (this.player) {
        this.player.currentTime = startTime;
        this.player.play();
      }
    },

    // 수정 모달 열기: 기존 캡션/멤버 불러오기
    handleModifyClick(segid) {
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
    },

    // 수정 모달 닫기
    closeModal() {
      this.showModifyModal = false;
    },

    // 수정 모달 '확인' 버튼: 수정 명령 전송
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

    // 멤버 추가/삭제
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

    // 병합 모달
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

    // 분할 모달
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

    // 생성 모달
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

    // "세그먼트" 메뉴 토글
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
