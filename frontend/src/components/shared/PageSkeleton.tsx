import { Skeleton, SkeletonItem } from "@fluentui/react-components";

export default function PageSkeleton() {
  return (
    <div style={{ padding: 48, maxWidth: 800, margin: "0 auto" }}>
      <Skeleton>
        <SkeletonItem style={{ width: 300, height: 32, marginBottom: 24 }} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem style={{ height: 120, marginBottom: 16 }} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem style={{ height: 120, marginBottom: 16 }} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem style={{ height: 120 }} />
      </Skeleton>
    </div>
  );
}
