const { createApp } = Vue;

createApp({
  data() {
    return {
      chatInput: "",
      chatMessages: [],
      player: null,

      // 수정 모달
      showModifyModal: false,
      modifySegId: null,
      modifyText: ""
    };
  },
  methods: {
    sendChat() { //전송 버튼을 누르면
      if (!this.chatInput.trim()) return;

      // 사용자 메시지 추가
      this.chatMessages.push({
        sender: "user",
        htmlContent: `<p>${this.escapeHtml(this.chatInput)}</p>`
      });

      axios.post("https://027e-58-72-151-123.ngrok-free.app/chat", { message: this.chatInput })
        .then(res => {
          const botMsg = res.data.response || "";
          // 세그먼트/수정하기 링크 치환
          console.log('botMsg:', botMsg)
          const transformed = this.transformLinks(botMsg);
          console.log('transformed:', transformed)


          // split 전: transformed는 긴 HTML 문자열
          // split: "<span class="segment-link"...>" 앞에서 잘라낸다
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
    transformLinks(text) {
      // [세그먼트ID=12 start=0.0]
      const reSeg = /\[세그먼트ID=(\d+)\s+start=(\d+(?:\.\d+)?)\]/g;
      let replaced = text.replace(reSeg, (match, segid, start) => {
        return `<span class="segment-link" data-segid="${segid}" data-start="${start}">[세그먼트 ${segid}]</span>`;
      });

      // [수정하기=12]
      const reMod = /\[수정하기=(\d+)\]/g;
      replaced = replaced.replace(reMod, (match, segid) => {
        return `<span class="modify-link" data-segid="${segid}">수정하기</span>`;
      });

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
    initYouTubePlayer() {
      this.player = new YT.Player("player", {
        height: "390",
        width: "640",
        videoId: "FuJ1RiLoq-M",
        events: {
          onReady: () => {
            console.log("YouTube 플레이어 준비 완료");
          }
        }
      });
    },
    // 세그먼트 클릭 -> 영상 이동
    handleSegmentClick(segid, start) {
      const startTime = parseFloat(start) || 0;
      if (this.player && typeof this.player.seekTo === "function") {
        this.player.seekTo(startTime, true);
      }
    },
    // 수정하기 클릭 -> 모달
    handleModifyClick(segid) {
      this.modifySegId = segid;
      this.modifyText = "";
      this.showModifyModal = true;
    },
    closeModal() {
      this.showModifyModal = false;
    },
    applyModify() { //??????????????????
      // "수정: 세그먼트ID=xx 내용=..."
      if (!this.modifyText.trim()) {
        alert("수정할 캡션을 입력하세요.");
        return;
      }
      const overrideCmd = `수정: 세그먼트ID=${this.modifySegId} 내용=${this.modifyText}`;
      // 사용자 메시지
      this.chatMessages.push({
        sender: "user",
        htmlContent: `<p>${this.escapeHtml(overrideCmd)}</p>`
      });
      // API 호출
      axios.post("https://027e-58-72-151-123.ngrok-free.app/chat", { message: overrideCmd })
        .then(res => {
          const botMsg = res.data.response || "";
          const finalMsg = `<p>${this.escapeHtml(botMsg)}</p>`;
          this.chatMessages.push({ sender: "bot", htmlContent: finalMsg });
        })
        .catch(error => {
          console.error("Error overriding caption:", error);
          this.chatMessages.push({
            sender: "bot",
            htmlContent: "<p>캡션 수정 중 오류가 발생했습니다.</p>"
          });
        });
      this.showModifyModal = false;
    }
  },
  mounted() {
    // YouTube IFrame API
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.body.appendChild(tag);
    window.onYouTubeIframeAPIReady = this.initYouTubePlayer;

    // 전역 이벤트
    document.addEventListener("click", (evt) => {
      const target = evt.target;
      if (!target) return;
      if (target.classList.contains("segment-link")) {
        const segid = target.getAttribute("data-segid");
        const start = target.getAttribute("data-start");
        this.handleSegmentClick(segid, start);
      }
      else if (target.classList.contains("modify-link")) {
        const segid = target.getAttribute("data-segid");
        this.handleModifyClick(segid);
      }
    });
  }
}).mount("#app");
