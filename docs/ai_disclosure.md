# Khai báo sử dụng Generative AI

| Công cụ | Dùng cho | Phạm vi | Cách kiểm chứng |
|---|---|---|---|
| ChatGPT | Soạn đặc tả ban đầu (`desc.md`, bản README đầu tiên) | Tài liệu thiết kế | Đối chiếu với rubric |
| Claude (Claude Code) | Lập kế hoạch (`PLAN.md`); viết mã pipeline dữ liệu, thuật toán KNNBaseline, đánh giá, fold-in, backend FastAPI, frontend React (gồm thiết kế giao diện Brutalist theo skill `brutalist-skill`), test, README | Phần lớn mã nguồn, test và tài liệu kỹ thuật | 112 test tự động (gồm test tính tay và đối chiếu với bản cài ngây thơ), tự chạy toàn bộ pipeline trên dữ liệu thật, kiểm tra giao diện trên trình duyệt, chạy thử README trên bản sao sạch |

Quy tắc áp dụng: mọi số liệu thực nghiệm (RMSE, NDCG, độ trễ...) được đo bằng chính các script trong repo trên dữ liệu MovieLens thật; AI không được dùng để tạo hay điền số liệu. Các quyết định thiết kế quan trọng (chọn KNNBaseline, cách chia dữ liệu, ngưỡng số rating tối thiểu và ràng buộc 25% danh mục, fold-in cho người dùng web) được ghi lại cùng lý do trong `PLAN.md`, `README.md` và trang Evaluation.

**Nhóm cần tự điền trước khi nộp:** phạm vi đóng góp của từng thành viên (xem `docs/contributions.md`) và xác nhận mỗi thành viên đã đọc, hiểu và giải thích được phần mình phụ trách khi Q&A. Không coi tài liệu này là bằng chứng rằng nhóm đã hiểu mã nguồn.
