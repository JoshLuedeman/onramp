import {
  makeStyles,
  tokens,
  Skeleton,
  SkeletonItem,
} from "@fluentui/react-components";

const useStyles = makeStyles({
  container: {
    paddingTop: "48px",
    paddingRight: "48px",
    paddingBottom: "48px",
    paddingLeft: "48px",
    maxWidth: "800px",
    marginTop: "0",
    marginBottom: "0",
    marginLeft: "auto",
    marginRight: "auto",
  },
  titleSkeleton: {
    width: "300px",
    height: "32px",
    marginBottom: tokens.spacingVerticalXXL,
  },
  blockSkeleton: {
    height: "120px",
    marginBottom: tokens.spacingVerticalL,
  },
  lastBlockSkeleton: {
    height: "120px",
  },
});

export default function PageSkeleton() {
  const styles = useStyles();
  return (
    <div className={styles.container}>
      <Skeleton>
        <SkeletonItem className={styles.titleSkeleton} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem className={styles.blockSkeleton} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem className={styles.blockSkeleton} />
      </Skeleton>
      <Skeleton>
        <SkeletonItem className={styles.lastBlockSkeleton} />
      </Skeleton>
    </div>
  );
}
