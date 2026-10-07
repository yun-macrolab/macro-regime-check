// 읽기 노트 — 뼈대. index.html의 applyView()가 setView(화면 이름, 뒤에 붙은 값)를 부른다.
// index.html 안의 el() · svgEl() · getJson() · calm()과 window.MacroCharts.lineChart를 쓸 수 있다(부를 때 이미 정의돼 있다).
window.ReadingNotes = (() => {
  function setView(view, arg) { /* view === "notes"일 때 #notes-wrap을 그린다 */ }
  return { setView };
})();
